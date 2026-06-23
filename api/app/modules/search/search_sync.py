import logging
from typing import Any

from elasticsearch import Elasticsearch

from app.db.elasticsearch_db import es_client
from app.db.models import Company, Contract


logger = logging.getLogger(__name__)


class SearchSyncService:
    def __init__(self, client: Elasticsearch | None = None) -> None:
        self.client = client or es_client

    def index_company(self, company: Company) -> None:
        document = {
            "id": str(company.id),
            "type": "company",
            "legal_name": company.legal_name,
            "trade_name": company.trade_name,
            "cnpj": company.cnpj,
            "city": company.city,
            "state_code": company.state_code,
            "registration_status": company.registration_status,
        }
        self._index("ongp_companies", str(company.id), document)

    def index_contract(self, contract: Contract) -> None:
        document = {
            "id": str(contract.id),
            "type": "contract",
            "contract_number": contract.contract_number,
            "process_number": contract.process_number,
            "object": contract.object,
            "modality": contract.modality,
            "status": contract.status,
            "total_value": (
                float(contract.total_value) if contract.total_value is not None else None
            ),
            "organization_id": (
                str(contract.organization_id) if contract.organization_id else None
            ),
            "supplier_company_id": (
                str(contract.supplier_company_id)
                if contract.supplier_company_id
                else None
            ),
        }
        self._index("ongp_contracts", str(contract.id), document)

    def index_contracts(self, contracts: list[Contract]) -> None:
        for contract in contracts:
            if contract.supplier is not None:
                self.index_company(contract.supplier)
            self.index_contract(contract)

    def _index(self, index: str, document_id: str, document: dict[str, Any]) -> None:
        try:
            self.client.index(index=index, id=document_id, document=document)
        except Exception:
            logger.exception("elasticsearch_index_failed")
