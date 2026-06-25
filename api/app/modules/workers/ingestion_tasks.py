import logging
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from app.core.celery_app import celery_app
from app.modules.graphs.sync_engine import MassiveGraphSyncEngine
from app.modules.ingestion.base_government_connector import (
    GovernmentConnectorError,
    RegistryGovernmentConnector,
    SourceConfig,
    build_connector,
    load_sources_registry,
)


logger = logging.getLogger(__name__)

SOURCE_ALIASES = {
    "all": "all",
    "camara": "camara_deputados",
    "camara_deputados": "camara_deputados",
    "senado": "senado_parlamentares",
    "senado_parlamentares": "senado_parlamentares",
    "tse": "tse_candidatos",
    "tse_candidatos": "tse_candidatos",
    "portal": "portal_transparencia_despesas",
    "portal_transparencia": "portal_transparencia_despesas",
    "portal_transparencia_despesas": "portal_transparencia_despesas",
    "portal_transparencia_contratos": "portal_transparencia_contratos",
    "comprasgov": "comprasgov_contratos",
    "comprasgov_contratos": "comprasgov_contratos",
    "receita": "receita_federal_cnpj",
    "receita_federal_cnpj": "receita_federal_cnpj",
}


@celery_app.task(name="app.modules.workers.ingestion_tasks.run_massive_ingestion")
def run_massive_ingestion(source_key: str) -> dict[str, Any]:
    registry = load_sources_registry()
    requested_key = SOURCE_ALIASES.get(source_key.strip().lower(), source_key.strip())
    engine = MassiveGraphSyncEngine(batch_size=5000)
    if not engine.connection.verify():
        return {
            "job": "massive_ingestion",
            "requested_source_key": source_key,
            "sources_processed": 0,
            "rows_collected": 0,
            "nodes_synced": 0,
            "results": [],
            "errors": [
                "Neo4j indisponivel. Suba a stack com perfil analytics/full para sincronizar o grafo."
            ],
        }
    engine.ensure_constraints()

    if requested_key == "all":
        selected_keys = [
            key
            for key, config in registry.items()
            if config.enabled and key in SOURCE_ALIASES.values()
        ]
    else:
        selected_keys = [requested_key]

    results: list[dict[str, Any]] = []
    for key in selected_keys:
        try:
            results.append(_run_single_source(key, registry, engine))
        except Exception as exc:
            logger.exception("massive_ingestion_source_failed", extra={"source_key": key})
            results.append(
                {
                    "source_key": key,
                    "status": "error",
                    "rows_collected": 0,
                    "nodes_synced": 0,
                    "errors": [str(exc)],
                }
            )

    errors = [
        error
        for result in results
        for error in result.get("errors", [])
    ]
    return {
        "job": "massive_ingestion",
        "requested_source_key": source_key,
        "sources_processed": len(results),
        "rows_collected": sum(int(item.get("rows_collected", 0)) for item in results),
        "nodes_synced": sum(int(item.get("nodes_synced", 0)) for item in results),
        "results": results,
        "errors": errors,
    }


def _run_single_source(
    source_key: str,
    registry: dict[str, SourceConfig],
    engine: MassiveGraphSyncEngine,
) -> dict[str, Any]:
    if source_key not in registry:
        raise GovernmentConnectorError(f"Fonte nao registrada: {source_key}")

    connector = build_connector(source_key, registry=registry)
    rows = _collect_rows(connector)
    sync_result = _sync_rows(engine, source_key, connector.config, rows)

    return {
        "source_key": source_key,
        "source_name": connector.config.name,
        "status": "success",
        "rows_collected": len(rows),
        "nodes_synced": sync_result["nodes_synced"],
        "sync_detail": sync_result,
        "errors": [],
    }


def _collect_rows(connector: RegistryGovernmentConnector) -> list[dict[str, Any]]:
    key = connector.config.key

    if key == "portal_transparencia_despesas":
        return _collect_portal_expenses(connector)
    if key == "senado_parlamentares":
        payload = connector.request("GET", connector.config.endpoints["default"]).json()
        return _senado_items(payload)
    if connector.config.source_type == "json":
        return connector.fetch_json_items()
    if connector.config.source_type == "csv":
        return list(connector.iter_csv_rows())
    if connector.config.source_type == "zip_csv":
        return list(
            connector.iter_zip_csv_rows(
                path_params={"year": _default_election_year()},
            )
        )

    raise GovernmentConnectorError(
        f"Tipo de fonte nao suportado: {connector.config.source_type}"
    )


def _collect_portal_expenses(
    connector: RegistryGovernmentConnector,
) -> list[dict[str, Any]]:
    target_date = date.today() - timedelta(days=1)
    rows: list[dict[str, Any]] = []
    for phase in (1, 2, 3):
        try:
            rows.extend(
                connector.fetch_json_items(
                    params={
                        "dataEmissao": target_date.strftime("%d/%m/%Y"),
                        "fase": phase,
                        "pagina": 1,
                    }
                )
            )
        except Exception as exc:
            logger.warning(
                "portal_massive_expenses_phase_failed",
                extra={"phase": phase, "error": str(exc)},
            )
    return rows


def _sync_rows(
    engine: MassiveGraphSyncEngine,
    source_key: str,
    config: SourceConfig,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    if not rows:
        return {"nodes_synced": 0, "kind": "empty"}

    model = config.destination_model.rsplit(".", 1)[-1]
    if model == "PersonCreate":
        people = [_person_row(source_key, row) for row in rows]
        return {"nodes_synced": engine.sync_people(people), "kind": "people"}

    if model == "CompanyCreate":
        companies = [_company_row(source_key, row) for row in rows]
        return {"nodes_synced": engine.sync_companies(companies), "kind": "companies"}

    if model == "ContractCreate":
        companies = [_supplier_company_row(source_key, row) for row in rows]
        organizations = [_organization_row(source_key, row) for row in rows]
        contracts = [_contract_row(source_key, row) for row in rows]
        synced_companies = engine.sync_companies(companies)
        synced_orgs = engine.sync_organizations(organizations)
        synced_contracts = engine.sync_contracts(contracts)
        return {
            "nodes_synced": synced_companies + synced_orgs + synced_contracts,
            "kind": "contracts",
            "companies": synced_companies,
            "organizations": synced_orgs,
            "contracts": synced_contracts,
        }

    if model == "ExpenseCreate":
        companies = [_supplier_company_row(source_key, row) for row in rows]
        expenses = [_expense_row(source_key, row) for row in rows]
        synced_companies = engine.sync_companies(companies)
        synced_expenses = engine.sync_expenses(expenses)
        return {
            "nodes_synced": synced_companies + synced_expenses,
            "kind": "expenses",
            "companies": synced_companies,
            "expenses": synced_expenses,
        }

    return {"nodes_synced": 0, "kind": "unsupported_model", "model": model}


def _person_row(source_key: str, row: dict[str, Any]) -> dict[str, Any]:
    if source_key == "camara_deputados":
        full_name = _text(row.get("nome")) or "Parlamentar sem nome"
        external_id = _text(row.get("id"))
        return {
            "id": _entity_id(source_key, external_id or full_name),
            "full_name": full_name,
            "normalized_name": _normalize_name(full_name),
            "masked_cpf": None,
            "birth_year": None,
            "data_origin": source_key,
            "external_id": external_id,
            "party_acronym": _upper(row.get("siglaPartido")),
            "state_code": _upper(row.get("siglaUf")),
            "email": _text(row.get("email")),
        }

    if source_key == "senado_parlamentares":
        identity = row.get("IdentificacaoParlamentar") or row.get("identificacaoParlamentar") or row
        full_name = (
            _text(identity.get("NomeCompletoParlamentar"))
            or _text(identity.get("NomeParlamentar"))
            or "Senador sem nome"
        )
        external_id = _text(
            identity.get("CodigoParlamentar")
            or identity.get("CodigoPublicoNaLegAtual")
        )
        return {
            "id": _entity_id(source_key, external_id or full_name),
            "full_name": full_name,
            "normalized_name": _normalize_name(full_name),
            "data_origin": source_key,
            "external_id": external_id,
            "party_acronym": _upper(identity.get("SiglaPartidoParlamentar")),
            "state_code": _upper(identity.get("UfParlamentar")),
            "email": _text(identity.get("EmailParlamentar")),
        }

    if source_key == "tse_candidatos":
        full_name = _text(row.get("NM_CANDIDATO") or row.get("NM_URNA_CANDIDATO")) or "Candidato sem nome"
        external_id = _text(row.get("SQ_CANDIDATO"))
        return {
            "id": _entity_id(source_key, external_id or full_name),
            "full_name": full_name,
            "normalized_name": _normalize_name(full_name),
            "masked_cpf": _mask_cpf(row.get("NR_CPF_CANDIDATO")),
            "data_origin": source_key,
            "external_id": external_id,
            "party_acronym": _upper(row.get("SG_PARTIDO")),
            "state_code": _upper(row.get("SG_UF")),
        }

    full_name = _text(row.get("full_name") or row.get("nome") or row.get("name")) or "Pessoa sem nome"
    return {
        "id": _entity_id(source_key, row.get("id") or row.get("cpf") or full_name),
        "full_name": full_name,
        "normalized_name": _normalize_name(full_name),
        "masked_cpf": _mask_cpf(row.get("cpf") or row.get("masked_cpf")),
        "data_origin": source_key,
    }


def _company_row(source_key: str, row: dict[str, Any]) -> dict[str, Any]:
    cnpj = _company_cnpj(
        row.get("cnpj")
        or row.get("CNPJ")
        or row.get("cnpj_basico")
        or row.get("cpfCnpj")
        or row.get("cpf_cnpj")
    )
    legal_name = _text(
        row.get("legal_name")
        or row.get("razao_social")
        or row.get("nome")
        or row.get("nomeRazaoSocial")
        or row.get("nomeFornecedor")
    )
    return {
        "id": _entity_id(source_key, cnpj or legal_name),
        "legal_name": legal_name or "Empresa sem nome",
        "trade_name": _text(row.get("trade_name") or row.get("nome_fantasia")),
        "cnpj": cnpj,
        "cnae": _text(row.get("cnae") or row.get("cnae_fiscal")),
        "city": _text(row.get("municipio") or row.get("city")),
        "state_code": _upper(row.get("uf") or row.get("state_code")),
        "registration_status": _text(row.get("situacao") or row.get("registration_status")),
    }


def _supplier_company_row(source_key: str, row: dict[str, Any]) -> dict[str, Any]:
    supplier = row.get("fornecedor") if isinstance(row.get("fornecedor"), dict) else {}
    cnpj = _company_cnpj(
        supplier.get("cnpj")
        or supplier.get("cpfCnpj")
        or row.get("cnpjFornecedor")
        or row.get("cpfCnpjFornecedor")
        or row.get("cnpjCpfFornecedor")
        or row.get("niFornecedor")
    )
    legal_name = _text(
        supplier.get("nome")
        or supplier.get("nomeRazaoSocial")
        or row.get("nomeFornecedor")
        or row.get("nomeRazaoSocialFornecedor")
        or row.get("fornecedor")
    )
    return {
        "id": _entity_id("company", cnpj or legal_name),
        "legal_name": legal_name or "Fornecedor sem nome",
        "cnpj": cnpj,
        "state_code": _upper(row.get("uf")),
        "registration_status": "ativo" if cnpj else None,
    }


def _organization_row(source_key: str, row: dict[str, Any]) -> dict[str, Any]:
    org = row.get("orgao") if isinstance(row.get("orgao"), dict) else {}
    unit = row.get("unidadeGestora") if isinstance(row.get("unidadeGestora"), dict) else {}
    name = _text(
        org.get("nome")
        or unit.get("nome")
        or row.get("nomeOrgao")
        or row.get("orgao")
        or row.get("unidadeGestora")
    )
    code = _text(
        org.get("codigo")
        or unit.get("codigo")
        or row.get("codigoOrgao")
        or row.get("codigoUnidadeGestora")
    )
    return {
        "id": _entity_id("organization", code or name),
        "name": name or "Orgao nao informado",
        "normalized_name": _normalize_name(name or "Orgao nao informado"),
        "cnpj": _company_cnpj(org.get("cnpj") or unit.get("cnpj")),
        "organization_type": "orgao_publico",
        "jurisdiction_level": "federal",
        "state_code": _upper(org.get("uf") or unit.get("uf") or row.get("uf")),
    }


def _contract_row(source_key: str, row: dict[str, Any]) -> dict[str, Any]:
    contract_number = _text(row.get("numero") or row.get("numeroContrato") or row.get("contract_number"))
    process_number = _text(row.get("processo") or row.get("numeroProcesso") or row.get("process_number"))
    supplier = _supplier_company_row(source_key, row)
    org = _organization_row(source_key, row)
    return {
        "id": _entity_id(source_key, contract_number or process_number or str(row)),
        "contract_number": contract_number,
        "process_number": process_number,
        "organization_id": org["id"],
        "supplier_company_id": supplier["id"],
        "object": _text(row.get("objeto") or row.get("descricaoObjeto") or row.get("object")),
        "modality": _text(row.get("modalidade") or row.get("modalidadeCompra")),
        "status": _text(row.get("status") or row.get("situacao")),
        "total_value": _float(
            row.get("valor")
            or row.get("valorGlobal")
            or row.get("valorContrato")
            or row.get("valorInicial")
            or row.get("valorInicialCompra")
        ),
    }


def _expense_row(source_key: str, row: dict[str, Any]) -> dict[str, Any]:
    supplier = _supplier_company_row(source_key, row)
    amount = _float(
        row.get("valor")
        or row.get("valorDocumento")
        or row.get("valorPago")
        or row.get("valorEmpenhado")
        or row.get("valorLiquido")
    )
    expense_date = _text(
        row.get("data")
        or row.get("dataDocumento")
        or row.get("dataPagamento")
        or row.get("dataEmissao")
    )
    fiscal_year = None
    if expense_date and len(expense_date) >= 4 and expense_date[:4].isdigit():
        fiscal_year = int(expense_date[:4])
    return {
        "id": _entity_id(source_key, row.get("id") or row.get("numeroDocumento") or str(row)),
        "company_id": supplier["id"],
        "expense_type": _text(row.get("tipo") or row.get("tipoDespesa") or row.get("fase")),
        "description": _text(row.get("descricao") or row.get("observacao") or row.get("historico")),
        "commitment_number": _text(row.get("numeroEmpenho") or row.get("numeroDocumento")),
        "amount": amount,
        "expense_date": expense_date,
        "fiscal_year": fiscal_year,
        "state_code": _upper(row.get("uf") or row.get("estado")),
    }


def _senado_items(payload: Any) -> list[dict[str, Any]]:
    current = payload
    for key in ("ListaParlamentarEmExercicio", "Parlamentares", "Parlamentar"):
        if not isinstance(current, dict):
            return []
        current = current.get(key)
    if isinstance(current, list):
        return [item for item in current if isinstance(item, dict)]
    if isinstance(current, dict):
        return [current]
    return []


def _default_election_year() -> int:
    current_year = date.today().year
    if current_year % 2 == 0:
        return current_year
    return current_year - 1


def _entity_id(namespace: str, value: Any) -> str:
    text = _text(value) or "unknown"
    return str(uuid5(NAMESPACE_URL, f"ongp:{namespace}:{text}"))


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _upper(value: Any) -> str | None:
    text = _text(value)
    return text.upper() if text else None


def _normalize_name(value: str) -> str:
    return " ".join(value.lower().split())


def _mask_cpf(value: Any) -> str | None:
    digits = "".join(char for char in str(value or "") if char.isdigit())
    if len(digits) != 11:
        return None
    return f"***.{digits[3:6]}.{digits[6:9]}-**"


def _company_cnpj(value: Any) -> str | None:
    digits = "".join(char for char in str(value or "") if char.isdigit())
    return digits if len(digits) == 14 else None


def _float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    text = str(value).strip()
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(Decimal(text))
    except (InvalidOperation, ValueError):
        return None
