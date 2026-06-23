import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from math import ceil
from typing import Any

from app.modules.ingestion.base_client import BaseIngestionClient, IngestionClientError
from app.schemas.core_schemas import ExpenseCreate, PersonCreate


logger = logging.getLogger(__name__)


class CamaraDadosAbertosClient(BaseIngestionClient):
    def __init__(self, timeout: float = 30.0) -> None:
        super().__init__(
            base_url="https://dadosabertos.camara.leg.br/api/v2",
            timeout=timeout,
        )

    def fetch_deputados(
        self,
        pagina: int = 1,
        itens: int = 100,
        ordenar_por: str = "nome",
    ) -> list[PersonCreate]:
        payload = self.get(
            "/deputados",
            params={
                "pagina": pagina,
                "itens": itens,
                "ordem": "ASC",
                "ordenarPor": ordenar_por,
            },
        )
        return [self.transform_deputado(item) for item in self._items(payload)]

    def fetch_deputados_pages(
        self,
        pagina: int = 1,
        paginas: int = 1,
        itens: int = 100,
        ordenar_por: str = "nome",
    ) -> list[PersonCreate]:
        politicians: list[PersonCreate] = []
        page_count = max(paginas, 1)
        page_size = max(1, min(itens, 100))

        for page_number in range(pagina, pagina + page_count):
            page_items = self.fetch_deputados(
                pagina=page_number,
                itens=page_size,
                ordenar_por=ordenar_por,
            )
            politicians.extend(page_items)
            if len(page_items) < page_size:
                break

        return politicians

    def fetch_deputado_despesas(
        self,
        deputado_id: str,
        ano: int,
        mes: int | None = None,
        pagina: int = 1,
        itens: int = 100,
    ) -> list[ExpenseCreate]:
        params: dict[str, Any] = {"ano": ano, "pagina": pagina, "itens": itens}
        if mes:
            params["mes"] = mes

        payload = self.get(f"/deputados/{deputado_id}/despesas", params=params)
        return [self.transform_expense(item) for item in self._items(payload)]

    def fetch_deputado_despesas_pages(
        self,
        deputado_id: str,
        ano: int,
        mes: int | None = None,
        limit: int = 100,
        itens: int = 100,
    ) -> list[ExpenseCreate]:
        if limit <= 0:
            return []

        page_size = max(1, min(itens, 100))
        max_pages = max(1, ceil(limit / page_size))
        expenses: list[ExpenseCreate] = []

        for page_number in range(1, max_pages + 1):
            page_items = self.fetch_deputado_despesas(
                deputado_id=deputado_id,
                ano=ano,
                mes=mes,
                pagina=page_number,
                itens=page_size,
            )
            expenses.extend(page_items)
            if len(page_items) < page_size or len(expenses) >= limit:
                break

        return expenses[:limit]

    def transform_deputado(self, item: dict[str, Any]) -> PersonCreate:
        full_name = self._text(item.get("nome")) or "Parlamentar sem nome"
        return PersonCreate(
            full_name=full_name,
            normalized_name=_normalize_name(full_name),
            data_origin="dados-abertos-camara",
            external_id=self._text(item.get("id")),
            party_acronym=self._upper_text(item.get("siglaPartido")),
            state_code=self._upper_text(item.get("siglaUf")),
            photo_url=self._text(item.get("urlFoto")),
            email=self._text(item.get("email")),
        )

    def transform_expense(self, item: dict[str, Any]) -> ExpenseCreate:
        expense_date = self._date(item.get("dataDocumento")) or date.today()
        return ExpenseCreate(
            expense_type=self._text(item.get("tipoDespesa")),
            description=self._text(item.get("nomeFornecedor")),
            amount=self._decimal(item.get("valorLiquido") or item.get("valorDocumento")),
            expense_date=expense_date,
            fiscal_year=expense_date.year,
            commitment_number=self._text(item.get("codDocumento") or item.get("numDocumento")),
            payment_number=self._text(item.get("numRessarcimento")),
        )

    def _items(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, dict) and isinstance(payload.get("dados"), list):
            return [item for item in payload["dados"] if isinstance(item, dict)]
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return []

    def _date(self, value: Any) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None

    def _decimal(self, value: Any) -> Decimal:
        if value is None:
            return Decimal("0")
        if isinstance(value, Decimal):
            return value
        if isinstance(value, int | float):
            return Decimal(str(value))
        try:
            return Decimal(str(value).replace(",", "."))
        except (InvalidOperation, ValueError):
            return Decimal("0")

    def _text(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _upper_text(self, value: Any) -> str | None:
        text = self._text(value)
        return text.upper() if text else None


def _normalize_name(value: str) -> str:
    return " ".join(value.lower().split())


class SenadoDadosAbertosClient(BaseIngestionClient):
    def __init__(self, timeout: float = 30.0) -> None:
        super().__init__(
            base_url="https://legis.senado.leg.br/dadosabertos",
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

    def fetch_senadores(self) -> list[PersonCreate]:
        payload = self.get("/senador/lista/atual")
        return [self.transform_senador(item) for item in self._senadores(payload)]

    def fetch_senador_despesas(self, senador_id: str, ano: int) -> list[ExpenseCreate]:
        try:
            payload = self.get(f"/senador/{senador_id}/gastos", params={"ano": ano})
        except IngestionClientError:
            logger.info(
                "senado_expenses_endpoint_unavailable",
                extra={"senador_id": senador_id, "ano": ano},
            )
            return []

        return [self.transform_expense(item) for item in self._items(payload)]

    def transform_senador(self, item: dict[str, Any]) -> PersonCreate:
        identity = item.get("IdentificacaoParlamentar") or item.get("identificacaoParlamentar") or item
        if not isinstance(identity, dict):
            identity = item

        full_name = (
            self._text(identity.get("NomeCompletoParlamentar"))
            or self._text(identity.get("NomeParlamentar"))
            or "Senador sem nome"
        )

        return PersonCreate(
            full_name=full_name,
            normalized_name=_normalize_name(full_name),
            data_origin="dados-abertos-senado",
            external_id=self._text(
                identity.get("CodigoParlamentar")
                or identity.get("CodigoPublicoNaLegAtual")
            ),
            party_acronym=self._upper_text(identity.get("SiglaPartidoParlamentar")),
            state_code=self._upper_text(identity.get("UfParlamentar")),
            photo_url=self._text(identity.get("UrlFotoParlamentar")),
            email=self._text(identity.get("EmailParlamentar")),
        )

    def transform_expense(self, item: dict[str, Any]) -> ExpenseCreate:
        expense_date = date.today()
        return ExpenseCreate(
            expense_type=self._text(item.get("TipoDespesa") or item.get("tipo") or "senado"),
            description=self._text(item.get("Fornecedor") or item.get("fornecedor")),
            amount=self._decimal(item.get("Valor") or item.get("valor")),
            expense_date=expense_date,
            fiscal_year=expense_date.year,
        )

    def _items(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, dict):
            stack = [payload]
            while stack:
                current = stack.pop()
                for value in current.values():
                    if isinstance(value, list):
                        return [item for item in value if isinstance(item, dict)]
                    if isinstance(value, dict):
                        stack.append(value)
        return []

    def _senadores(self, payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, dict):
            return []

        current: Any = payload
        for key in ("ListaParlamentarEmExercicio", "Parlamentares", "Parlamentar"):
            if not isinstance(current, dict):
                return []
            current = current.get(key)

        if isinstance(current, list):
            return [item for item in current if isinstance(item, dict)]
        if isinstance(current, dict):
            return [current]
        return []

    def _decimal(self, value: Any) -> Decimal:
        if value is None:
            return Decimal("0")
        if isinstance(value, Decimal):
            return value
        if isinstance(value, int | float):
            return Decimal(str(value))
        try:
            return Decimal(str(value).replace(",", "."))
        except (InvalidOperation, ValueError):
            return Decimal("0")

    def _text(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _upper_text(self, value: Any) -> str | None:
        text = self._text(value)
        return text.upper() if text else None
