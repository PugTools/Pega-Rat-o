import csv
import io
import logging
import unicodedata
import zipfile
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.core.config import settings
from app.modules.ingestion.salary_reference import (
    SALARY_REFERENCE_SOURCE,
    SALARY_REFERENCE_YEAR,
    annual_salary_for_role,
    asset_salary_ratio,
)
from app.schemas.core_schemas import PersonCreate


logger = logging.getLogger(__name__)

TSE_CANDIDATES_URL = (
    "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/"
    "consulta_cand_{year}.zip"
)
TSE_ASSETS_URL = (
    "https://cdn.tse.jus.br/estatistica/sead/odsele/bem_candidato/"
    "bem_candidato_{year}.zip"
)


@dataclass(frozen=True)
class TsePoliticalRecord:
    person: PersonCreate
    role_name: str
    branch: str
    jurisdiction_level: str
    municipality_code: str | None = None


class TseDadosAbertosClient:
    def __init__(self, timeout: float = 180.0) -> None:
        self.timeout = timeout
        self.headers = {
            "Accept": "application/zip,text/csv,*/*",
            "User-Agent": "ONGP-PEGA-RATAO/0.1 (+observatorio-gastos-publicos)",
        }

    def fetch_elected_candidates(
        self,
        year: int,
        state_code: str | None = None,
        limit_per_role: int = 50,
        role_names: set[str] | None = None,
        only_elected: bool = True,
    ) -> list[TsePoliticalRecord]:
        limit = None if limit_per_role <= 0 else max(1, limit_per_role)
        roles = role_names or default_roles_for_year(year)
        quotas = {role: 0 for role in roles}
        records: list[TsePoliticalRecord] = []
        state_filter = _upper_text(state_code)

        archive = self._download_candidates_zip(year)
        asset_totals = self._safe_fetch_asset_totals(year=year, state_code=state_filter)
        with zipfile.ZipFile(io.BytesIO(archive)) as zip_file:
            for file_name in self._candidate_csv_names(zip_file, state_filter):
                with zip_file.open(file_name) as raw_file:
                    text_file = io.TextIOWrapper(raw_file, encoding="latin-1", newline="")
                    reader = csv.DictReader(text_file, delimiter=";")
                    for row in reader:
                        record = self.transform_candidate(
                            row,
                            year=year,
                            asset_totals=asset_totals,
                        )
                        if record is None:
                            continue
                        if state_filter and record.person.state_code != state_filter:
                            continue
                        if record.role_name not in roles:
                            continue
                        if only_elected and not _is_elected(row.get("DS_SIT_TOT_TURNO")):
                            continue
                        if limit is not None and quotas[record.role_name] >= limit:
                            continue

                        records.append(record)
                        quotas[record.role_name] += 1
                        if limit is not None and quotas and all(
                            count >= limit for count in quotas.values()
                        ):
                            return records

        return records

    def transform_candidate(
        self,
        row: dict[str, Any],
        year: int,
        asset_totals: dict[str, Decimal] | None = None,
    ) -> TsePoliticalRecord | None:
        role_name = map_tse_role(row.get("DS_CARGO"))
        if not role_name:
            return None

        full_name = (
            _text(row.get("NM_CANDIDATO"))
            or _text(row.get("NM_URNA_CANDIDATO"))
            or "Candidato sem nome"
        )
        state_code = _upper_text(row.get("SG_UF"))
        municipality_code = _text(row.get("SG_UE"))
        external_id = _text(row.get("SQ_CANDIDATO"))
        branch, jurisdiction_level = classify_role(role_name)
        declared_assets_value = (asset_totals or {}).get(external_id or "")
        salary_reference_value = annual_salary_for_role(role_name)

        return TsePoliticalRecord(
            person=PersonCreate(
                full_name=full_name,
                normalized_name=_normalize_name(full_name),
                masked_cpf=_mask_cpf(row.get("NR_CPF_CANDIDATO")),
                data_origin=f"dados-abertos-tse-{year}",
                external_id=external_id,
                party_acronym=_upper_text(row.get("SG_PARTIDO")),
                state_code=state_code,
                declared_assets_value=declared_assets_value,
                declared_assets_year=year if declared_assets_value is not None else None,
                salary_reference_value=salary_reference_value,
                salary_reference_year=SALARY_REFERENCE_YEAR if salary_reference_value is not None else None,
                salary_reference_source=SALARY_REFERENCE_SOURCE if salary_reference_value is not None else None,
                asset_salary_ratio=asset_salary_ratio(declared_assets_value, role_name),
            ),
            role_name=role_name,
            branch=branch,
            jurisdiction_level=jurisdiction_level,
            municipality_code=municipality_code,
        )

    def _download_candidates_zip(self, year: int) -> bytes:
        url = TSE_CANDIDATES_URL.format(year=year)
        try:
            with httpx.Client(
                timeout=self.timeout,
                headers=self.headers,
                verify=settings.HTTP_VERIFY_SSL,
                follow_redirects=True,
            ) as client:
                response = client.get(url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Falha ao baixar candidatos TSE {year}: {exc}") from exc

        return response.content

    def _download_assets_zip(self, year: int) -> bytes:
        url = TSE_ASSETS_URL.format(year=year)
        try:
            with httpx.Client(
                timeout=self.timeout,
                headers=self.headers,
                verify=settings.HTTP_VERIFY_SSL,
                follow_redirects=True,
            ) as client:
                response = client.get(url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Falha ao baixar bens TSE {year}: {exc}") from exc

        return response.content

    def _safe_fetch_asset_totals(
        self,
        year: int,
        state_code: str | None,
    ) -> dict[str, Decimal]:
        try:
            return self._fetch_asset_totals(year=year, state_code=state_code)
        except Exception:
            logger.exception("tse_asset_totals_fetch_failed", extra={"year": year})
            return {}

    def _fetch_asset_totals(
        self,
        year: int,
        state_code: str | None,
    ) -> dict[str, Decimal]:
        archive = self._download_assets_zip(year)
        totals: dict[str, Decimal] = {}
        with zipfile.ZipFile(io.BytesIO(archive)) as zip_file:
            for file_name in self._asset_csv_names(zip_file, state_code):
                with zip_file.open(file_name) as raw_file:
                    text_file = io.TextIOWrapper(raw_file, encoding="latin-1", newline="")
                    reader = csv.DictReader(text_file, delimiter=";")
                    for row in reader:
                        candidate_id = _text(row.get("SQ_CANDIDATO"))
                        if not candidate_id:
                            continue
                        totals[candidate_id] = totals.get(candidate_id, Decimal("0")) + _decimal(
                            row.get("VR_BEM_CANDIDATO")
                        )
        return totals

    def _candidate_csv_names(
        self,
        zip_file: zipfile.ZipFile,
        state_code: str | None,
    ) -> list[str]:
        names = [
            name
            for name in zip_file.namelist()
            if name.lower().endswith(".csv")
            and "consulta_cand" in name.lower()
        ]
        if not state_code:
            return names

        preferred = [
            name
            for name in names
            if f"_{state_code.lower()}." in name.lower()
            or f"_{state_code.lower()}_" in name.lower()
        ]
        return preferred or names

    def _asset_csv_names(
        self,
        zip_file: zipfile.ZipFile,
        state_code: str | None,
    ) -> list[str]:
        names = [
            name
            for name in zip_file.namelist()
            if name.lower().endswith(".csv")
            and "bem_candidato" in name.lower()
        ]
        if not state_code:
            return names

        preferred = [
            name
            for name in names
            if f"_{state_code.lower()}." in name.lower()
            or f"_{state_code.lower()}_" in name.lower()
        ]
        return preferred or names


def default_roles_for_year(year: int) -> set[str]:
    if year % 4 == 0:
        return {"Prefeito", "Vice-prefeito", "Vereador"}

    return {
        "Presidente",
        "Vice-presidente",
        "Governador",
        "Vice-governador",
        "Senador",
        "Deputado Federal",
        "Deputado Estadual",
        "Deputado Distrital",
    }


def map_tse_role(value: Any) -> str | None:
    normalized = _normalize_text(value)
    mapping = {
        "PRESIDENTE": "Presidente",
        "VICE PRESIDENTE": "Vice-presidente",
        "GOVERNADOR": "Governador",
        "VICE GOVERNADOR": "Vice-governador",
        "SENADOR": "Senador",
        "DEPUTADO FEDERAL": "Deputado Federal",
        "DEPUTADO ESTADUAL": "Deputado Estadual",
        "DEPUTADO DISTRITAL": "Deputado Distrital",
        "PREFEITO": "Prefeito",
        "VICE PREFEITO": "Vice-prefeito",
        "VEREADOR": "Vereador",
    }
    return mapping.get(normalized)


def classify_role(role_name: str) -> tuple[str, str]:
    executive_roles = {
        "Presidente",
        "Vice-presidente",
        "Governador",
        "Vice-governador",
        "Prefeito",
        "Vice-prefeito",
    }
    if role_name in executive_roles:
        branch = "executivo"
    else:
        branch = "legislativo"

    if role_name in {"Prefeito", "Vice-prefeito", "Vereador"}:
        return branch, "municipal"
    if role_name in {"Governador", "Vice-governador", "Deputado Estadual", "Deputado Distrital"}:
        return branch, "estadual"
    return branch, "federal"


def _is_elected(value: Any) -> bool:
    normalized = _normalize_text(value)
    if not normalized:
        return False
    if "NAO ELEITO" in normalized or "SUPLENTE" in normalized:
        return False
    return "ELEITO" in normalized


def _normalize_name(value: str) -> str:
    return " ".join(value.lower().split())


def _normalize_text(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.upper().replace("-", " ").split())


def _mask_cpf(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = "".join(char for char in text if char.isdigit())
    if len(digits) != 11:
        return None
    return f"***.{digits[3:6]}.{digits[6:9]}-**"


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


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _upper_text(value: Any) -> str | None:
    text = _text(value)
    return text.upper() if text else None
