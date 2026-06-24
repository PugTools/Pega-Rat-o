from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from app.modules.ingestion.base_client import BaseIngestionClient
from app.schemas.core_schemas import CompanyCreate, ContractCreate, OrganizationCreate


DEFAULT_CONTRACT_ORG_CODES = (
    "26000",  # Ministerio da Educacao
    "25000",  # Ministerio da Saude
    "20101",  # Presidencia da Republica
    "52000",  # Ministerio da Defesa
)


class ComprasGovClient(BaseIngestionClient):
    def __init__(self, timeout: float = 45.0) -> None:
        super().__init__(
            base_url="https://dadosabertos.compras.gov.br",
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

    def fetch_contratos(
        self,
        data_inicio: date,
        data_fim: date,
        pagina: int = 1,
        codigo_orgao: str | None = None,
        tamanho_pagina: int = 50,
    ) -> list[ContractCreate]:
        org_codes = (codigo_orgao,) if codigo_orgao else DEFAULT_CONTRACT_ORG_CODES
        contracts: list[ContractCreate] = []

        for org_code in org_codes:
            payload = self.get(
                "/modulo-contratos/1_consultarContratos",
                params={
                    "pagina": pagina,
                    "tamanhoPagina": max(10, min(tamanho_pagina, 500)),
                    "codigoOrgao": org_code,
                    "dataVigenciaInicialMin": data_inicio.isoformat(),
                    "dataVigenciaInicialMax": data_fim.isoformat(),
                },
            )
            contracts.extend(self.transform_contract(item) for item in self._items(payload))

        return contracts

    def transform_contract(self, item: dict[str, Any]) -> ContractCreate:
        supplier_cnpj = _digits(item.get("niFornecedor"))
        organization_code = _text(
            item.get("codigoUnidadeGestora")
            or item.get("codigoUnidadeGestoraOrigemContrato")
            or item.get("codigoOrgao")
        )
        organization_name = _text(
            item.get("nomeUnidadeGestora")
            or item.get("nomeUnidadeGestoraOrigemContrato")
            or item.get("nomeOrgao")
        )
        contract_number = _text(item.get("numeroContrato"))
        process_number = _text(item.get("processo"))

        return ContractCreate(
            contract_number=contract_number,
            process_number=process_number,
            object=_text(item.get("objeto")),
            modality=_text(item.get("nomeModalidadeCompra") or item.get("codigoModalidadeCompra")),
            status=_text(item.get("nomeTipo") or item.get("nomeCategoria") or "registrado"),
            starts_at=_date(item.get("dataVigenciaInicial")),
            ends_at=_date(item.get("dataVigenciaFinal")),
            total_value=_decimal(
                item.get("valorGlobal")
                or item.get("valorAcumulado")
                or item.get("valorParcela")
                or 0
            ),
            supplier_payload=CompanyCreate(
                legal_name=_text(item.get("nomeRazaoSocialFornecedor")) or "Fornecedor sem nome",
                cnpj=supplier_cnpj or f"sem-cnpj-{_safe_key(contract_number, process_number)}",
                registration_status="ativo",
            )
            if supplier_cnpj or item.get("nomeRazaoSocialFornecedor")
            else None,
            organization_payload=OrganizationCreate(
                name=organization_name or "Orgao nao informado",
                normalized_name=_normalize_name(organization_name or "Orgao nao informado"),
                cnpj=None,
                organization_type="orgao_publico",
                jurisdiction_level="federal",
                municipality_code=organization_code,
            )
            if organization_name or organization_code
            else None,
        )

    def _items(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in ("resultado", "data", "items", "content"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        return []


def _date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not value:
        return None
    text = str(value).strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int | float):
        return Decimal(str(value))
    text = str(value).strip()
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif text.count(".") > 1:
        text = text.replace(".", "")
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _digits(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = "".join(char for char in text if char.isdigit())
    return digits or None


def _normalize_name(value: str) -> str:
    return " ".join(value.lower().split())


def _safe_key(*values: str | None) -> str:
    text = "-".join(value for value in values if value)
    return _digits(text) or "desconhecido"


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
