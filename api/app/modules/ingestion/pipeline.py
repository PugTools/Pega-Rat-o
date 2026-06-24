import logging
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.cache import delete_pattern
from app.core.config import settings
from app.db import repositories
from app.db.models import Contract, Expense
from app.modules.alerts.risk_rules import (
    check_abnormal_growth,
    check_expense_fragmentation,
    check_supplier_concentration,
)
from app.modules.alerts.webhooks import dispatch_alert_webhook
from app.modules.graphs.sync_service import GraphSyncService
from app.modules.ia.nlp_processor import NLPProcessor
from app.modules.ingestion.compras_gov_client import ComprasGovClient
from app.modules.ingestion.transparencia_gov import PortalTransparenciaClient
from app.modules.search.search_sync import SearchSyncService
from app.modules.settings.risk_settings import get_risk_settings
from app.schemas.core_schemas import ContractCreate, ExpenseCreate


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestionResult:
    contracts_found: int
    contracts_saved: int
    expenses_found: int
    expenses_saved: int
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "contracts_found": self.contracts_found,
            "contracts_saved": self.contracts_saved,
            "expenses_found": self.expenses_found,
            "expenses_saved": self.expenses_saved,
            "errors": self.errors,
        }


class IngestionPipeline:
    def __init__(
        self,
        db: Session,
        client: PortalTransparenciaClient | None = None,
        compras_client: ComprasGovClient | None = None,
        graph_sync_service: GraphSyncService | None = None,
        search_sync_service: SearchSyncService | None = None,
        nlp_processor: NLPProcessor | None = None,
    ) -> None:
        self.db = db
        self.client = client or PortalTransparenciaClient(
            api_key=settings.portal_transparencia_api_key
        )
        self.compras_client = compras_client or ComprasGovClient()
        self.graph_sync_service = graph_sync_service or GraphSyncService()
        self.search_sync_service = search_sync_service or SearchSyncService()
        self.nlp_processor = nlp_processor or NLPProcessor(self.graph_sync_service)

    def run_daily_ingestion(
        self,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        codigo_orgao: str | None = None,
        pagina: int = 1,
    ) -> IngestionResult:
        end_date = data_fim or date.today()
        expenses_start_date = data_inicio or end_date - timedelta(days=1)
        contracts_start_date = data_inicio or end_date - timedelta(days=365)

        errors: list[str] = []
        contracts = self._fetch_contracts(
            contracts_start_date,
            end_date,
            pagina,
            codigo_orgao,
            errors,
        )
        expenses = self._fetch_expenses(
            expenses_start_date,
            end_date,
            pagina,
            codigo_orgao,
            errors,
        )

        saved_contracts = self._persist_contracts(contracts, errors)
        saved_expenses = self._persist_expenses(expenses, errors)

        if saved_contracts or saved_expenses:
            self._sync_graph(saved_contracts)
            self._sync_search(saved_contracts)
            self._process_nlp(saved_contracts, saved_expenses)
            self._generate_and_save_alerts(saved_contracts, saved_expenses)
            self.db.commit()
        else:
            self.db.rollback()

        return IngestionResult(
            contracts_found=len(contracts),
            contracts_saved=len(saved_contracts),
            expenses_found=len(expenses),
            expenses_saved=len(saved_expenses),
            errors=errors,
        )

    def _fetch_contracts(
        self,
        data_inicio: date,
        data_fim: date,
        pagina: int,
        codigo_orgao: str | None,
        errors: list[str],
    ) -> list[ContractCreate]:
        portal_error: str | None = None
        try:
            raw_contracts = self.client.fetch_contratos(
                data_inicio=data_inicio,
                data_fim=data_fim,
                pagina=pagina,
                codigo_orgao=codigo_orgao,
            )
        except Exception as exc:
            portal_error = f"portal_contracts_fetch_failed: {exc}"
            raw_contracts = []

        if not raw_contracts:
            try:
                raw_contracts = self.compras_client.fetch_contratos(
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    pagina=pagina,
                    codigo_orgao=codigo_orgao,
                )
            except Exception as exc:
                if portal_error:
                    errors.append(portal_error)
                errors.append(f"comprasgov_contracts_fetch_failed: {exc}")
                return []

        contracts: list[ContractCreate] = []
        for item in raw_contracts:
            try:
                contracts.append(ContractCreate.model_validate(item))
            except ValidationError as exc:
                errors.append(f"contract_validation_failed: {exc}")
        return contracts

    def _fetch_expenses(
        self,
        data_inicio: date,
        data_fim: date,
        pagina: int,
        codigo_orgao: str | None,
        errors: list[str],
    ) -> list[ExpenseCreate]:
        try:
            raw_expenses = self.client.fetch_despesas(
                data_inicio=data_inicio,
                data_fim=data_fim,
                pagina=pagina,
                codigo_orgao=codigo_orgao,
            )
        except Exception as exc:
            errors.append(f"expenses_fetch_failed: {exc}")
            return []

        expenses: list[ExpenseCreate] = []
        for item in raw_expenses:
            try:
                expenses.append(ExpenseCreate.model_validate(item))
            except ValidationError as exc:
                errors.append(f"expense_validation_failed: {exc}")
        return expenses

    def _persist_contracts(
        self,
        contracts: list[ContractCreate],
        errors: list[str],
    ) -> list[Contract]:
        saved: list[Contract] = []
        for contract in contracts:
            try:
                organization_id = contract.organization_id
                supplier_company_id = contract.supplier_company_id

                if contract.organization_payload is not None:
                    organization = repositories.upsert_organization(
                        self.db,
                        contract.organization_payload,
                    )
                    organization_id = organization.id

                if contract.supplier_payload is not None:
                    supplier = repositories.upsert_company(
                        self.db,
                        contract.supplier_payload,
                    )
                    supplier_company_id = supplier.id

                saved.append(
                    repositories.upsert_contract(
                        self.db,
                        contract.model_copy(
                            update={
                                "organization_id": organization_id,
                                "supplier_company_id": supplier_company_id,
                            }
                        ),
                    )
                )
            except Exception as exc:
                errors.append(f"contract_persist_failed: {exc}")
        return saved

    def _persist_expenses(
        self,
        expenses: list[ExpenseCreate],
        errors: list[str],
    ) -> list[Expense]:
        saved: list[Expense] = []
        for expense in expenses:
            try:
                saved.append(repositories.upsert_expense(self.db, expense))
            except Exception as exc:
                errors.append(f"expense_persist_failed: {exc}")
        return saved

    def _sync_graph(self, contracts: list[Contract]) -> None:
        if not contracts:
            return

        try:
            for contract in contracts:
                if contract.supplier is not None:
                    _ = contract.supplier.legal_name
                if contract.organization is not None:
                    _ = contract.organization.name
            self.graph_sync_service.sync_contracts(contracts)
        except Exception as exc:
            logger.exception("neo4j_sync_failed")
            return

    def _generate_and_save_alerts(
        self,
        contracts: list[Contract],
        expenses: list[Expense],
    ) -> None:
        try:
            alerts = []
            settings = get_risk_settings()
            alerts.extend(
                check_expense_fragmentation(
                    expenses,
                    legal_limit=Decimal(settings["expense_fragmentation_legal_limit"]),
                    minimum_count=int(settings["expense_fragmentation_minimum_count"]),
                    window_days=int(settings["expense_fragmentation_window_days"]),
                )
            )
            alerts.extend(
                check_supplier_concentration(
                    expenses,
                    concentration_threshold=Decimal(settings["supplier_concentration_threshold"]),
                    minimum_total_amount=Decimal(settings["supplier_concentration_minimum_total_amount"]),
                )
            )

            for contract in contracts:
                historical_contracts = [
                    item
                    for item in contracts
                    if item.id != contract.id
                    and item.organization_id == contract.organization_id
                ]
                alert = check_abnormal_growth(
                    contract,
                    historical_contracts,
                    growth_threshold=Decimal(settings["abnormal_growth_threshold"]),
                    minimum_history=int(settings["abnormal_growth_minimum_history"]),
                )
                if alert:
                    alerts.append(alert)

            repositories.save_alerts(self.db, alerts)
            delete_pattern("alerts:*")
            for alert in alerts:
                dispatch_alert_webhook(alert)
        except Exception:
            logger.exception("risk_alert_persistence_failed")

    def _sync_search(self, contracts: list[Contract]) -> None:
        if not contracts:
            return

        try:
            for contract in contracts:
                if contract.supplier is not None:
                    _ = contract.supplier.legal_name
            self.search_sync_service.index_contracts(contracts)
        except Exception:
            logger.exception("elasticsearch_sync_failed")

    def _process_nlp(
        self,
        contracts: list[Contract],
        expenses: list[Expense],
    ) -> None:
        try:
            for contract in contracts:
                self.nlp_processor.process_contract_text(contract)
            for expense in expenses:
                self.nlp_processor.process_expense_text(expense)
        except Exception:
            logger.exception("nlp_processing_failed")
