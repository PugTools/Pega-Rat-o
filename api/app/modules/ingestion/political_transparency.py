import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.cache import delete_pattern
from app.db import repositories
from app.db.models import Expense, Person
from app.modules.alerts.risk_rules import check_asset_salary_ratio
from app.modules.graphs.sync_service import GraphSyncService
from app.modules.ingestion.camara_senado_client import (
    CamaraDadosAbertosClient,
    SenadoDadosAbertosClient,
)
from app.modules.ingestion.tse_client import TseDadosAbertosClient
from app.schemas.core_schemas import ExpenseCreate, PersonCreate, PublicRoleCreate


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PoliticalRecord:
    person: PersonCreate
    role_name: str | None = None
    branch: str | None = None
    jurisdiction_level: str | None = None
    municipality_code: str | None = None


@dataclass(frozen=True)
class PoliticalIngestionResult:
    politicians_found: int
    politicians_saved: int
    expenses_found: int
    expenses_saved: int
    expense_year: int
    source_counts: dict[str, int]
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "politicians_found": self.politicians_found,
            "politicians_saved": self.politicians_saved,
            "expenses_found": self.expenses_found,
            "expenses_saved": self.expenses_saved,
            "expense_year": self.expense_year,
            "source_counts": self.source_counts,
            "errors": self.errors,
        }


class PoliticalTransparencyIngestion:
    def __init__(
        self,
        db: Session,
        client: CamaraDadosAbertosClient | None = None,
        camara_client: CamaraDadosAbertosClient | None = None,
        senado_client: SenadoDadosAbertosClient | None = None,
        tse_client: TseDadosAbertosClient | None = None,
        graph_sync_service: GraphSyncService | None = None,
    ) -> None:
        self.db = db
        self.camara_client = camara_client or client or CamaraDadosAbertosClient()
        self.senado_client = senado_client or SenadoDadosAbertosClient()
        self.tse_client = tse_client or TseDadosAbertosClient()
        self.graph_sync_service = graph_sync_service or GraphSyncService()

    def run(
        self,
        pagina: int = 1,
        itens: int = 25,
        ano: int | None = None,
        despesas_por_politico: int = 100,
        paginas_camara: int = 1,
        incluir_senado: bool = True,
        despesas_senado: bool = False,
        incluir_tse: bool = False,
        anos_tse: list[int] | None = None,
        limite_tse_por_cargo: int = 50,
        uf_tse: str | None = None,
        patrimonio_tse: bool = True,
        sync_graph: bool = True,
    ) -> PoliticalIngestionResult:
        expense_year = ano or date.today().year
        errors: list[str] = []
        source_counts: dict[str, int] = {}

        politicians = self._fetch_politicians(
            pagina=pagina,
            itens=itens,
            paginas_camara=paginas_camara,
            incluir_senado=incluir_senado,
            incluir_tse=incluir_tse,
            anos_tse=anos_tse,
            limite_tse_por_cargo=limite_tse_por_cargo,
            uf_tse=uf_tse,
            patrimonio_tse=patrimonio_tse,
            errors=errors,
            source_counts=source_counts,
        )

        if not politicians and errors:
            return PoliticalIngestionResult(
                politicians_found=0,
                politicians_saved=0,
                expenses_found=0,
                expenses_saved=0,
                expense_year=expense_year,
                source_counts=source_counts,
                errors=errors,
            )

        saved_people: list[Person] = []
        saved_expenses: list[Expense] = []
        people_to_enrich: list[tuple[Person, PersonCreate]] = []
        expenses_found = 0

        for politician_payload in politicians:
            person_payload = politician_payload.person
            try:
                person = repositories.upsert_person(self.db, person_payload)
                self._upsert_public_role(person, politician_payload, errors)
                saved_people.append(person)
                people_to_enrich.append((person, person_payload))
            except Exception as exc:
                errors.append(
                    f"politician_persist_failed:{person_payload.external_id}: {exc}"
                )
                continue

        if saved_people:
            self.db.commit()
            delete_pattern("persons:*")

        for person, person_payload in people_to_enrich:
            politician_expenses = self._fetch_expenses_for_person(
                politician_payload=person_payload,
                expense_year=expense_year,
                despesas_por_politico=despesas_por_politico,
                despesas_senado=despesas_senado,
                errors=errors,
            )
            expenses_found += len(politician_expenses)

            persisted_expenses = self._persist_person_expenses(
                person=person,
                expenses=politician_expenses,
                errors=errors,
            )
            saved_expenses.extend(persisted_expenses)
            self._update_person_expense_summary(person, persisted_expenses, expense_year)
            if sync_graph:
                self._sync_person_to_graph(person, errors)

        if errors:
            logger.warning("political_ingestion_completed_with_errors: %s", errors)

        self._generate_asset_alerts(saved_people, errors)
        self.db.commit()
        delete_pattern("persons:*")
        delete_pattern("alerts:*")

        return PoliticalIngestionResult(
            politicians_found=len(politicians),
            politicians_saved=len(saved_people),
            expenses_found=expenses_found,
            expenses_saved=len(saved_expenses),
            expense_year=expense_year,
            source_counts=source_counts,
            errors=errors,
        )

    def _fetch_politicians(
        self,
        pagina: int,
        itens: int,
        paginas_camara: int,
        incluir_senado: bool,
        incluir_tse: bool,
        anos_tse: list[int] | None,
        limite_tse_por_cargo: int,
        uf_tse: str | None,
        patrimonio_tse: bool,
        errors: list[str],
        source_counts: dict[str, int],
    ) -> list[PoliticalRecord]:
        politicians: list[PoliticalRecord] = []

        try:
            deputados = self.camara_client.fetch_deputados_pages(
                pagina=pagina,
                paginas=paginas_camara,
                itens=itens,
            )
            source_counts["dados-abertos-camara"] = len(deputados)
            politicians.extend(
                PoliticalRecord(
                    person=deputado,
                    role_name="Deputado Federal",
                    branch="legislativo",
                    jurisdiction_level="federal",
                )
                for deputado in deputados
            )
        except Exception as exc:
            errors.append(f"camara_politicians_fetch_failed: {exc}")

        if incluir_senado:
            try:
                senadores = self.senado_client.fetch_senadores()
                source_counts["dados-abertos-senado"] = len(senadores)
                politicians.extend(
                    PoliticalRecord(
                        person=senador,
                        role_name="Senador",
                        branch="legislativo",
                        jurisdiction_level="federal",
                    )
                    for senador in senadores
                )
            except Exception as exc:
                errors.append(f"senado_politicians_fetch_failed: {exc}")

        if incluir_tse:
            politicians.extend(
                self._fetch_tse_politicians(
                    anos_tse=anos_tse or [2024, 2022],
                    limite_tse_por_cargo=limite_tse_por_cargo,
                    uf_tse=uf_tse,
                    patrimonio_tse=patrimonio_tse,
                    errors=errors,
                    source_counts=source_counts,
                )
            )

        return politicians

    def _fetch_tse_politicians(
        self,
        anos_tse: list[int],
        limite_tse_por_cargo: int,
        uf_tse: str | None,
        patrimonio_tse: bool,
        errors: list[str],
        source_counts: dict[str, int],
    ) -> list[PoliticalRecord]:
        politicians: list[PoliticalRecord] = []

        for year in anos_tse:
            try:
                records = self.tse_client.fetch_elected_candidates(
                    year=year,
                    state_code=uf_tse,
                    limit_per_role=limite_tse_por_cargo,
                    include_assets=patrimonio_tse,
                )
                source_counts[f"dados-abertos-tse-{year}"] = len(records)
                politicians.extend(
                    PoliticalRecord(
                        person=record.person,
                        role_name=record.role_name,
                        branch=record.branch,
                        jurisdiction_level=record.jurisdiction_level,
                        municipality_code=record.municipality_code,
                    )
                    for record in records
                )
            except Exception as exc:
                errors.append(f"tse_politicians_fetch_failed:{year}: {exc}")

        return politicians

    def _fetch_expenses_for_person(
        self,
        politician_payload: PersonCreate,
        expense_year: int,
        despesas_por_politico: int,
        despesas_senado: bool,
        errors: list[str],
    ) -> list[ExpenseCreate]:
        if not politician_payload.external_id:
            return []

        if politician_payload.data_origin == "dados-abertos-senado" and not despesas_senado:
            return []
        if politician_payload.data_origin not in {
            "dados-abertos-camara",
            "dados-abertos-senado",
        }:
            return []

        try:
            if politician_payload.data_origin == "dados-abertos-senado":
                expenses = self.senado_client.fetch_senador_despesas(
                    senador_id=politician_payload.external_id,
                    ano=expense_year,
                )
            else:
                expenses = self.camara_client.fetch_deputado_despesas_pages(
                    deputado_id=politician_payload.external_id,
                    ano=expense_year,
                    limit=despesas_por_politico,
                )
        except Exception as exc:
            errors.append(
                f"politician_expenses_fetch_failed:{politician_payload.external_id}: {exc}"
            )
            return []

        return expenses[:despesas_por_politico]

    def _upsert_public_role(
        self,
        person: Person,
        politician_payload: PoliticalRecord,
        errors: list[str],
    ) -> None:
        role_name = politician_payload.role_name

        if not role_name:
            return

        try:
            repositories.upsert_public_role(
                self.db,
                PublicRoleCreate(
                    person_id=person.id,
                    role_name=role_name,
                    branch=politician_payload.branch,
                    jurisdiction_level=politician_payload.jurisdiction_level,
                    state_code=politician_payload.person.state_code,
                    municipality_code=politician_payload.municipality_code,
                    party_acronym=politician_payload.person.party_acronym,
                ),
            )
        except Exception as exc:
            errors.append(f"politician_role_persist_failed:{person.id}: {exc}")

    def _persist_person_expenses(
        self,
        person: Person,
        expenses: list[ExpenseCreate],
        errors: list[str],
    ) -> list[Expense]:
        saved: list[Expense] = []
        for expense in expenses:
            try:
                payload = expense.model_copy(
                    update={
                        "person_id": person.id,
                        "state_code": person.state_code,
                    }
                )
                saved.append(repositories.upsert_expense(self.db, payload))
            except Exception as exc:
                errors.append(f"politician_expense_persist_failed:{person.id}: {exc}")
        return saved

    def _update_person_expense_summary(
        self,
        person: Person,
        expenses: list[Expense],
        expense_year: int,
    ) -> None:
        if not expenses:
            return

        total = sum((expense.amount or Decimal("0")) for expense in expenses)
        person.latest_expense_total = total
        person.latest_expense_year = expense_year
        self.db.flush()

    def _sync_person_to_graph(self, person: Person, errors: list[str]) -> None:
        try:
            self.graph_sync_service.sync_person(person)
        except Exception as exc:
            logger.exception("politician_graph_sync_failed")
            errors.append(f"politician_graph_sync_failed:{person.id}: {exc}")

    def _generate_asset_alerts(
        self,
        people: list[Person],
        errors: list[str],
    ) -> None:
        if not people:
            return

        try:
            alerts = check_asset_salary_ratio(people)
            repositories.save_alerts(self.db, alerts)
        except Exception as exc:
            logger.exception("politician_asset_alert_persist_failed")
            errors.append(f"politician_asset_alert_persist_failed: {exc}")
