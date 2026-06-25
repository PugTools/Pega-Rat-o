import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from math import ceil
from typing import Any

from app.modules.ingestion.base_client import BaseIngestionClient, IngestionClientError
from app.modules.ingestion.salary_reference import (
    SALARY_REFERENCE_SOURCE,
    SALARY_REFERENCE_YEAR,
    annual_salary_for_role,
)
from app.schemas.core_schemas import CompanyCreate, ExpenseCreate, PersonCreate


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
        role_name = "Deputado Federal"
        salary_reference_value = annual_salary_for_role(role_name)
        return PersonCreate(
            full_name=full_name,
            normalized_name=_normalize_name(full_name),
            data_origin="dados-abertos-camara",
            external_id=self._text(item.get("id")),
            party_acronym=self._upper_text(item.get("siglaPartido")),
            state_code=self._upper_text(item.get("siglaUf")),
            photo_url=self._text(item.get("urlFoto")),
            email=self._text(item.get("email")),
            salary_reference_value=salary_reference_value,
            salary_reference_year=SALARY_REFERENCE_YEAR if salary_reference_value is not None else None,
            salary_reference_source=SALARY_REFERENCE_SOURCE if salary_reference_value is not None else None,
        )

    def transform_expense(self, item: dict[str, Any]) -> ExpenseCreate:
        expense_date = self._date(item.get("dataDocumento")) or date.today()
        supplier_name = self._text(item.get("nomeFornecedor"))
        supplier_cnpj = _company_cnpj(item.get("cnpjCpfFornecedor"))
        document_url = self._text(item.get("urlDocumento"))
        document_number = self._text(item.get("codDocumento") or item.get("numDocumento"))

        # Mapeamento federal: CNPJ_FORNECEDOR -> supplier_payload.cnpj,
        # NOME_FORNECEDOR -> supplier_payload.legal_name, NUMERO_DOCUMENTO ->
        # commitment_number, URL_DOCUMENTO -> document_url/raw_documents.
        return ExpenseCreate(
            expense_type=self._text(item.get("tipoDespesa")),
            description=self._text(
                item.get("tipoDocumento")
                or item.get("nomeFornecedor")
                or item.get("tipoDespesa")
            ),
            amount=self._decimal(item.get("valorLiquido") or item.get("valorDocumento")),
            expense_date=expense_date,
            fiscal_year=expense_date.year,
            commitment_number=document_number,
            payment_number=self._text(item.get("numRessarcimento")),
            supplier_payload=_supplier_payload(supplier_name, supplier_cnpj),
            document_url=document_url,
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


def _company_cnpj(value: Any) -> str | None:
    if value is None:
        return None
    digits = "".join(char for char in str(value) if char.isdigit())
    return digits if len(digits) == 14 else None


def _supplier_payload(name: str | None, cnpj: str | None) -> CompanyCreate | None:
    if not cnpj:
        return None
    return CompanyCreate(
        legal_name=name or "Fornecedor sem nome",
        cnpj=cnpj,
        registration_status="ativo",
    )


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
        legislativo_expenses = self._fetch_senador_despesas_legislativo(
            senador_id=senador_id,
            ano=ano,
        )
        if legislativo_expenses:
            return legislativo_expenses

        return self._fetch_senador_despesas_ceaps(senador_id=senador_id, ano=ano)

    def _fetch_senador_despesas_legislativo(
        self,
        senador_id: str,
        ano: int,
    ) -> list[ExpenseCreate]:
        try:
            payload = self.get(f"/senador/{senador_id}/gastos", params={"ano": ano})
        except IngestionClientError:
            return []

        return [self.transform_expense(item) for item in self._items(payload)]

    def _fetch_senador_despesas_ceaps(
        self,
        senador_id: str,
        ano: int,
    ) -> list[ExpenseCreate]:
        try:
            payload = self.get(
                f"https://adm.senado.gov.br/adm-dadosabertos/api/v1/senadores/despesas_ceaps/{ano}"
            )
        except IngestionClientError:
            logger.info(
                "senado_expenses_endpoint_unavailable",
                extra={"senador_id": senador_id, "ano": ano},
            )
            return []

        return [
            self.transform_expense(item)
            for item in self._items(payload)
            if self._text(item.get("codSenador")) == str(senador_id)
        ]

    def transform_senador(self, item: dict[str, Any]) -> PersonCreate:
        identity = item.get("IdentificacaoParlamentar") or item.get("identificacaoParlamentar") or item
        if not isinstance(identity, dict):
            identity = item

        full_name = (
            self._text(identity.get("NomeCompletoParlamentar"))
            or self._text(identity.get("NomeParlamentar"))
            or "Senador sem nome"
        )
        role_name = "Senador"
        salary_reference_value = annual_salary_for_role(role_name)

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
            salary_reference_value=salary_reference_value,
            salary_reference_year=SALARY_REFERENCE_YEAR if salary_reference_value is not None else None,
            salary_reference_source=SALARY_REFERENCE_SOURCE if salary_reference_value is not None else None,
        )

    def transform_expense(self, item: dict[str, Any]) -> ExpenseCreate:
        expense_date = self._date(item.get("data")) or date.today()
        supplier_name = self._text(
            item.get("fornecedor")
            or item.get("Fornecedor")
            or item.get("nomeFornecedor")
        )
        supplier_cnpj = _company_cnpj(
            item.get("cnpjCpfFornecedor")
            or item.get("cpfCnpjFornecedor")
            or item.get("cnpjFornecedor")
        )
        document_number = self._text(
            item.get("id")
            or item.get("documento")
            or item.get("numDocumento")
        )
        document_url = self._text(
            item.get("urlDocumento")
            or item.get("URLDocumento")
            or item.get("url")
        )

        # Mapeamento federal: CNPJ_FORNECEDOR -> supplier_payload.cnpj,
        # NOME_FORNECEDOR -> supplier_payload.legal_name, NUMERO_DOCUMENTO ->
        # commitment_number, URL_DOCUMENTO -> document_url/raw_documents.
        return ExpenseCreate(
            expense_type=self._text(item.get("tipoDespesa") or item.get("TipoDespesa") or "CEAPS"),
            description=self._text(
                item.get("detalhamento")
                or item.get("tipoDocumento")
                or supplier_name
            ),
            amount=self._decimal(
                item.get("valorReembolsado")
                or item.get("Valor")
                or item.get("valor")
            ),
            expense_date=expense_date,
            fiscal_year=expense_date.year,
            commitment_number=document_number,
            payment_number=self._text(item.get("documento")),
            supplier_payload=_supplier_payload(supplier_name, supplier_cnpj),
            document_url=document_url,
        )

    def _items(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
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
        text = str(value).strip()
        if "," in text:
            text = text.replace(".", "").replace(",", ".")
        elif text.count(".") > 1:
            text = text.replace(".", "")
        try:
            return Decimal(text)
        except (InvalidOperation, ValueError):
            return Decimal("0")

    def _date(self, value: Any) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None

    def _text(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _upper_text(self, value: Any) -> str | None:
        text = self._text(value)
        return text.upper() if text else None
