import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.config import settings
from app.modules.ingestion.base_client import BaseIngestionClient
from app.schemas.core_schemas import ContractCreate, ExpenseCreate


logger = logging.getLogger(__name__)


class PortalTransparenciaClient(BaseIngestionClient):
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.portaldatransparencia.gov.br/api-de-dados",
        timeout: float = 30.0,
    ) -> None:
        headers = {"chave-api-dados": settings.PORTAL_TRANSPARENCIA_API_KEY}
        if api_key is not None:
            headers["chave-api-dados"] = api_key
        super().__init__(base_url=base_url, timeout=timeout, headers=headers)

    def fetch_despesas(
        self,
        data_inicio: date,
        data_fim: date,
        pagina: int = 1,
        codigo_orgao: str | None = None,
    ) -> list[ExpenseCreate]:
        params: dict[str, Any] = {
            "dataInicio": data_inicio.strftime("%d/%m/%Y"),
            "dataFim": data_fim.strftime("%d/%m/%Y"),
            "pagina": pagina,
        }
        if codigo_orgao:
            params["codigoOrgao"] = codigo_orgao

        payload = self.get("/despesas/documentos", params=params)
        items = self._items(payload)
        logger.debug(
            "portal_transparencia_expenses_payload",
            extra={
                "payload_type": type(payload).__name__,
                "items": len(items),
                "first_keys": sorted(items[0].keys()) if items else [],
            },
        )
        return [self.transform_expense(item) for item in items]

    def fetch_contratos(
        self,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        pagina: int = 1,
        codigo_orgao: str | None = None,
    ) -> list[ContractCreate]:
        params: dict[str, Any] = {"pagina": pagina}
        if data_inicio:
            params["dataInicio"] = data_inicio.strftime("%d/%m/%Y")
        if data_fim:
            params["dataFim"] = data_fim.strftime("%d/%m/%Y")
        if codigo_orgao:
            params["codigoOrgao"] = codigo_orgao

        payload = self.get("/contratos", params=params)
        items = self._items(payload)
        logger.debug(
            "portal_transparencia_contracts_payload",
            extra={
                "payload_type": type(payload).__name__,
                "items": len(items),
                "first_keys": sorted(items[0].keys()) if items else [],
            },
        )
        return [self.transform_contract(item) for item in items]

    def transform_expense(self, item: dict[str, Any]) -> ExpenseCreate:
        amount = self._decimal(
            item.get("valor")
            or item.get("valorDocumento")
            or item.get("valorPago")
            or item.get("valorEmpenhado")
            or 0
        )
        expense_date = self._date(
            item.get("data")
            or item.get("dataDocumento")
            or item.get("dataPagamento")
            or item.get("dataEmissao")
        )

        return ExpenseCreate(
            amount=amount,
            expense_date=expense_date or date.today(),
            fiscal_year=(expense_date or date.today()).year,
            expense_type=self._text(item.get("tipo") or item.get("fase")),
            description=self._text(self._expense_description(item)),
            commitment_number=self._text(
                item.get("numeroEmpenho") or item.get("documentoResumido")
            ),
            payment_number=self._text(item.get("numeroPagamento")),
            state_code=self._text(
                item.get("uf")
                or item.get("estado")
                or self._nested_value(item, "unidadeGestora", "uf")
                or self._nested_value(item, "orgao", "uf")
            ),
            municipality_code=self._text(
                item.get("codigoMunicipio") or item.get("municipio")
            ),
        )

    def transform_contract(self, item: dict[str, Any]) -> ContractCreate:
        return ContractCreate(
            contract_number=self._text(item.get("numero") or item.get("numeroContrato")),
            process_number=self._text(item.get("processo") or item.get("numeroProcesso")),
            object=self._text(item.get("objeto") or item.get("descricaoObjeto")),
            modality=self._text(
                self._nested_value(item, "modalidadeCompra", "descricao")
                or item.get("modalidadeCompra")
                or item.get("modalidade")
            ),
            status=self._text(
                self._nested_value(item, "situacao", "descricao")
                or item.get("situacao")
                or item.get("status")
            ),
            signed_at=self._date(
                item.get("dataAssinatura") or item.get("dataAssinaturaContrato")
            ),
            starts_at=self._date(
                item.get("dataInicioVigencia") or item.get("dataInicioVigenciaContrato")
            ),
            ends_at=self._date(
                item.get("dataFimVigencia") or item.get("dataFimVigenciaContrato")
            ),
            total_value=self._decimal(
                item.get("valorInicialCompra")
                or item.get("valorInicial")
                or item.get("valorContrato")
                or item.get("valorGlobal")
                or item.get("valor")
            ),
        )

    def _items(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in ("data", "items", "resultado", "content"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
            return [payload]
        return []

    def _date(self, value: Any) -> date | None:
        if isinstance(value, date):
            return value
        if not value:
            return None

        text_value = str(value).strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(text_value[:10], fmt).date()
            except ValueError:
                continue
        return None

    def _decimal(self, value: Any) -> Decimal:
        if value is None:
            return Decimal("0")
        if isinstance(value, Decimal):
            return value
        if isinstance(value, int | float):
            return Decimal(str(value))

        text_value = str(value).strip()
        if "," in text_value:
            text_value = text_value.replace(".", "").replace(",", ".")
        elif text_value.count(".") > 1:
            text_value = text_value.replace(".", "")

        try:
            return Decimal(text_value)
        except (InvalidOperation, ValueError):
            logger.warning(
                "portal_transparencia_invalid_decimal",
                extra={"value": str(value)[:80]},
            )
            return Decimal("0")

    def _text(self, value: Any) -> str | None:
        if value is None:
            return None
        text_value = str(value).strip()
        return text_value or None

    def _expense_description(self, item: dict[str, Any]) -> Any:
        if item.get("descricao") or item.get("observacao") or item.get("historico"):
            return item.get("descricao") or item.get("observacao") or item.get("historico")

        favored = item.get("favorecido")
        if isinstance(favored, dict):
            return favored.get("nome") or favored.get("nomeFavorecido")

        return None

    def _nested_value(self, item: dict[str, Any], key: str, nested_key: str) -> Any:
        value = item.get(key)
        if isinstance(value, dict):
            return value.get(nested_key)
        return None
