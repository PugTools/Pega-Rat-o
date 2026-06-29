import logging
from decimal import Decimal
from typing import Any

from app.db.neo4j_database import Neo4jConnection, neo4j_connection
from app.modules.alerts.risk_rules import RiskAlert


logger = logging.getLogger(__name__)


def find_cross_nepotism(
    connection: Neo4jConnection | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    graph = connection or neo4j_connection
    safe_limit = _safe_limit(limit)
    rows = graph.execute_query(
        """
        MATCH (politician:Person)-[:OCCUPIES]->(role:PublicRole)
        OPTIONAL MATCH (role)-[:IN_ORGANIZATION]->(role_org:Organization)
        MATCH (partner:Person)-[:SOCIO_DE]->(company:Company)
        MATCH (company)-[:VENCEU_LICITACAO|SUPPLIES]->(target)
        OPTIONAL MATCH (contract_org:Organization)-[:CONTRATOU]->(target)
        WITH politician, role, role_org, partner, company, target, contract_org,
             last(split(toLower(coalesce(politician.full_name, '')), ' ')) AS politician_surname,
             last(split(toLower(coalesce(partner.full_name, '')), ' ')) AS partner_surname
        WHERE
            (partner)-[:PARENTE_DE]-(politician)
            OR (
                politician.masked_cpf IS NOT NULL
                AND partner.masked_cpf IS NOT NULL
                AND politician.masked_cpf = partner.masked_cpf
            )
            OR (
                politician_surname <> ''
                AND partner_surname <> ''
                AND politician_surname = partner_surname
            )
        WITH politician, role, role_org, partner, company, target, contract_org
        WHERE role_org IS NULL
           OR contract_org IS NULL
           OR role_org.id = contract_org.id
           OR role.state_code = contract_org.state_code
           OR role.municipality_code = contract_org.municipality_code
        RETURN
            company.id AS company_id,
            company.legal_name AS company_name,
            company.cnpj AS company_cnpj,
            politician.id AS politician_id,
            politician.full_name AS politician_name,
            partner.id AS partner_id,
            partner.full_name AS partner_name,
            role.role_name AS role_name,
            coalesce(role_org.id, contract_org.id) AS organization_id,
            coalesce(role_org.name, contract_org.name) AS organization_name,
            target.id AS target_id,
            labels(target)[0] AS target_type,
            coalesce(target.total_value, target.estimated_value, 0) AS target_value
        ORDER BY target_value DESC
        LIMIT $limit
        """,
        {"limit": safe_limit},
    )

    return [
        RiskAlert(
            entity_type="company",
            entity_id=str(row["company_id"]),
            alert_type="cross_nepotism_graph",
            severity="critical",
            score=Decimal("91.000"),
            title="Possivel nepotismo cruzado em fornecedor",
            explanation=(
                "O grafo encontrou fornecedor vencedor conectado a socio com "
                "parentesco, CPF mascarado ou sobrenome em comum com agente publico "
                "relacionado a orgao/territorio do contrato."
            ),
            evidence=row,
        ).to_dict()
        for row in rows
        if row.get("company_id")
    ]


def find_campaign_donor_winners(
    connection: Neo4jConnection | None = None,
    min_contract_value: float = 1000000.0,
    limit: int = 100,
) -> list[dict[str, Any]]:
    graph = connection or neo4j_connection
    safe_limit = _safe_limit(limit)
    safe_min_contract_value = _safe_amount(min_contract_value)
    rows = graph.execute_query(
        """
        MATCH (donor:Donor)-[donation:DOOU_PARA]->(politician:Person)
        MATCH (politician)-[:OCCUPIES]->(role:PublicRole)
        OPTIONAL MATCH (role)-[:IN_ORGANIZATION]->(role_org:Organization)
        MATCH (company:Company)-[award:VENCEU_LICITACAO]->(contract:Contract)
        WHERE
            (company)-[:SAME_DOCUMENT_AS]->(donor)
            OR EXISTS {
                MATCH (partner:Person)-[:SOCIO_DE]->(company)
                WHERE partner.id = donor.id
                   OR partner.masked_cpf = donor.document
                   OR toLower(partner.full_name) = toLower(donor.name)
            }
        OPTIONAL MATCH (contract_org:Organization)-[:CONTRATOU]->(contract)
        WITH donor, donation, politician, role, role_org, company, award, contract, contract_org,
             coalesce(contract.total_value, award.amount, 0) AS contract_value
        WHERE contract_value >= $min_contract_value
          AND (
              role_org IS NULL
              OR contract_org IS NULL
              OR role_org.id = contract_org.id
              OR role.state_code = contract_org.state_code
              OR role.municipality_code = contract_org.municipality_code
          )
        RETURN
            company.id AS company_id,
            company.legal_name AS company_name,
            company.cnpj AS company_cnpj,
            donor.id AS donor_id,
            donor.name AS donor_name,
            donor.document AS donor_document,
            donation.amount AS donation_amount,
            donation.election_year AS election_year,
            politician.id AS politician_id,
            politician.full_name AS politician_name,
            role.role_name AS role_name,
            contract.id AS contract_id,
            contract.contract_number AS contract_number,
            contract_value,
            contract_org.id AS organization_id,
            contract_org.name AS organization_name
        ORDER BY contract_value DESC, donation_amount DESC
        LIMIT $limit
        """,
        {"min_contract_value": safe_min_contract_value, "limit": safe_limit},
    )

    return [
        RiskAlert(
            entity_type="company",
            entity_id=str(row["company_id"]),
            alert_type="campaign_donor_winner_graph",
            severity="critical",
            score=Decimal("94.000"),
            title="Doador de campanha venceu contrato relevante",
            explanation=(
                "Empresa ou socio vinculado a doador de campanha aparece como "
                "vencedor de contrato relevante associado ao agente publico ou "
                "ao seu territorio de atuacao."
            ),
            evidence=row,
        ).to_dict()
        for row in rows
        if row.get("company_id")
    ]


def find_enforced_supplier_winners(
    connection: Neo4jConnection | None = None,
    min_contract_value: float = 500000.0,
    limit: int = 100,
) -> list[dict[str, Any]]:
    graph = connection or neo4j_connection
    safe_limit = _safe_limit(limit)
    safe_min_contract_value = _safe_amount(min_contract_value)
    rows = graph.execute_query(
        """
        MATCH (company:Company)-[:AUTUADO_POR]->(action:EnforcementAction)
        MATCH (company)-[award:VENCEU_LICITACAO]->(contract:Contract)
        WITH company, action, award, contract,
             coalesce(contract.total_value, award.amount, 0) AS contract_value
        WHERE contract_value >= $min_contract_value
        OPTIONAL MATCH (org:Organization)-[:CONTRATOU]->(contract)
        RETURN
            company.id AS company_id,
            company.legal_name AS company_name,
            company.cnpj AS company_cnpj,
            action.id AS enforcement_id,
            action.agency AS agency,
            action.reason AS reason,
            action.amount AS enforcement_amount,
            action.date AS enforcement_date,
            contract.id AS contract_id,
            contract.contract_number AS contract_number,
            contract_value,
            org.id AS organization_id,
            org.name AS organization_name
        ORDER BY contract_value DESC
        LIMIT $limit
        """,
        {"min_contract_value": safe_min_contract_value, "limit": safe_limit},
    )

    return [
        RiskAlert(
            entity_type="company",
            entity_id=str(row["company_id"]),
            alert_type="enforced_supplier_winner_graph",
            severity="high",
            score=Decimal("86.000"),
            title="Fornecedor autuado venceu contrato relevante",
            explanation=(
                "Fornecedor com autuacao registrada em base publica tambem aparece "
                "como vencedor de contrato relevante."
            ),
            evidence=row,
        ).to_dict()
        for row in rows
        if row.get("company_id")
    ]


def run_graph_audit_suite(
    connection: Neo4jConnection | None = None,
) -> list[dict[str, Any]]:
    graph = connection or neo4j_connection
    alerts: list[dict[str, Any]] = []
    for rule_name, rule in (
        ("cross_nepotism", find_cross_nepotism),
        ("campaign_donor_winners", find_campaign_donor_winners),
        ("enforced_supplier_winners", find_enforced_supplier_winners),
    ):
        try:
            alerts.extend(rule(graph))
        except Exception as exc:
            logger.warning(
                "graph_audit_rule_failed",
                extra={
                    "rule": rule_name,
                    "error": str(exc),
                },
            )
    return alerts


def _safe_limit(value: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 100
    return max(1, min(parsed, 500))


def _safe_amount(value: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(parsed, 1_000_000_000_000.0))
