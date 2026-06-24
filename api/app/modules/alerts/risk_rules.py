from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.db.neo4j_database import Neo4jConnection, neo4j_connection


@dataclass(frozen=True)
class RiskAlert:
    entity_type: str
    entity_id: str
    alert_type: str
    severity: str
    score: Decimal
    title: str
    explanation: str
    evidence: dict[str, Any]
    status: str = "open"
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["score"] = str(self.score)
        payload["created_at"] = self.created_at.isoformat()
        return payload


def check_expense_fragmentation(
    expenses: Iterable[Any],
    legal_limit: Decimal = Decimal("50000.00"),
    minimum_count: int = 3,
    window_days: int = 30,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, int], list[Any]] = defaultdict(list)

    for expense in expenses:
        organization_id = _entity_id(expense, "organization_id")
        company_id = _entity_id(expense, "company_id")
        expense_date = _date_value(expense, "expense_date")
        amount = _decimal_value(expense, "amount")

        if not organization_id or not company_id or not expense_date:
            continue
        if amount >= legal_limit:
            continue

        bucket = expense_date.toordinal() // window_days
        grouped[(organization_id, company_id, bucket)].append(expense)

    alerts: list[dict[str, Any]] = []
    for (organization_id, company_id, _bucket), bucket_expenses in grouped.items():
        if len(bucket_expenses) < minimum_count:
            continue

        total = sum((_decimal_value(item, "amount") for item in bucket_expenses), Decimal("0"))
        if total < legal_limit:
            continue

        alerts.append(
            RiskAlert(
                entity_type="company",
                entity_id=company_id,
                alert_type="expense_fragmentation",
                severity=_severity(total / legal_limit),
                score=_score(total / legal_limit, base=55),
                title="Possivel fragmentacao de despesas",
                explanation=(
                    f"Foram encontradas {len(bucket_expenses)} despesas abaixo do "
                    f"limite configurado que somam {total} para o mesmo fornecedor "
                    f"e orgao em janela de {window_days} dias."
                ),
                evidence={
                    "organization_id": organization_id,
                    "company_id": company_id,
                    "expense_count": len(bucket_expenses),
                    "total_amount": str(total),
                    "legal_limit": str(legal_limit),
                    "expense_ids": [_entity_id(item, "id") for item in bucket_expenses],
                },
            ).to_dict()
        )

    return alerts


def check_supplier_concentration(
    expenses: Iterable[Any],
    concentration_threshold: Decimal = Decimal("0.70"),
    minimum_total_amount: Decimal = Decimal("100000.00"),
) -> list[dict[str, Any]]:
    totals_by_org: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    totals_by_pair: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal("0"))

    for expense in expenses:
        organization_id = _entity_id(expense, "organization_id")
        company_id = _entity_id(expense, "company_id")
        amount = _decimal_value(expense, "amount")

        if not organization_id or not company_id:
            continue

        totals_by_org[organization_id] += amount
        totals_by_pair[(organization_id, company_id)] += amount

    alerts: list[dict[str, Any]] = []
    for (organization_id, company_id), supplier_total in totals_by_pair.items():
        org_total = totals_by_org[organization_id]
        if org_total <= 0 or supplier_total < minimum_total_amount:
            continue

        concentration = supplier_total / org_total
        if concentration < concentration_threshold:
            continue

        alerts.append(
            RiskAlert(
                entity_type="company",
                entity_id=company_id,
                alert_type="supplier_concentration",
                severity=_severity(concentration / concentration_threshold),
                score=_score(concentration / concentration_threshold, base=60),
                title="Concentracao elevada em fornecedor",
                explanation=(
                    f"Fornecedor concentra {concentration:.1%} dos pagamentos "
                    f"analisados do orgao, acima do limite de "
                    f"{concentration_threshold:.0%}."
                ),
                evidence={
                    "organization_id": organization_id,
                    "company_id": company_id,
                    "supplier_total": str(supplier_total),
                    "organization_total": str(org_total),
                    "concentration": str(concentration),
                    "threshold": str(concentration_threshold),
                },
            ).to_dict()
        )

    return alerts


def check_abnormal_growth(
    current_contract: Any,
    historical_contracts: Iterable[Any],
    growth_threshold: Decimal = Decimal("3.00"),
    minimum_history: int = 3,
) -> dict[str, Any] | None:
    current_value = _decimal_value(current_contract, "total_value")
    current_id = _entity_id(current_contract, "id")
    comparable_values = [
        _decimal_value(contract, "total_value")
        for contract in historical_contracts
        if _decimal_value(contract, "total_value") > 0
    ]

    if current_value <= 0 or len(comparable_values) < minimum_history:
        return None

    historical_average = sum(comparable_values, Decimal("0")) / Decimal(
        len(comparable_values)
    )
    if historical_average <= 0:
        return None

    growth_ratio = current_value / historical_average
    if growth_ratio < growth_threshold:
        return None

    return RiskAlert(
        entity_type="contract",
        entity_id=current_id,
        alert_type="abnormal_contract_growth",
        severity=_severity(growth_ratio / growth_threshold),
        score=_score(growth_ratio / growth_threshold, base=65),
        title="Crescimento anormal de valor contratual",
        explanation=(
            f"Contrato apresenta valor {growth_ratio:.2f}x superior a media "
            f"historica de contratos comparaveis."
        ),
        evidence={
            "contract_id": current_id,
            "current_value": str(current_value),
            "historical_average": str(historical_average),
            "historical_count": len(comparable_values),
            "growth_ratio": str(growth_ratio),
            "threshold": str(growth_threshold),
        },
    ).to_dict()


def check_asset_salary_ratio(
    persons: Iterable[Any],
    medium_threshold: Decimal = Decimal("8.00"),
    high_threshold: Decimal = Decimal("15.00"),
    critical_threshold: Decimal = Decimal("30.00"),
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []

    for person in persons:
        person_id = _entity_id(person, "id")
        full_name = _field(person, "full_name") or "Agente publico"
        declared_assets = _decimal_value(person, "declared_assets_value")
        annual_salary = _decimal_value(person, "salary_reference_value")
        ratio = _decimal_value(person, "asset_salary_ratio")

        if not person_id or declared_assets <= 0 or annual_salary <= 0:
            continue
        if ratio < medium_threshold:
            continue

        if ratio >= critical_threshold:
            severity = "critical"
            score = Decimal("92.000")
        elif ratio >= high_threshold:
            severity = "high"
            score = Decimal("82.000")
        else:
            severity = "medium"
            score = Decimal("68.000")

        alerts.append(
            RiskAlert(
                entity_type="person",
                entity_id=person_id,
                alert_type="asset_salary_ratio",
                severity=severity,
                score=score,
                title="Patrimonio declarado acima da referencia salarial",
                explanation=(
                    f"{full_name} declarou patrimonio equivalente a {ratio:.1f} "
                    "anos da remuneracao anual de referencia do cargo. "
                    "O indicador nao prova irregularidade, mas prioriza auditoria."
                ),
                evidence={
                    "person_id": person_id,
                    "full_name": str(full_name),
                    "declared_assets_value": str(declared_assets),
                    "annual_salary_reference": str(annual_salary),
                    "asset_salary_ratio": str(ratio),
                    "medium_threshold": str(medium_threshold),
                    "high_threshold": str(high_threshold),
                    "critical_threshold": str(critical_threshold),
                    "declared_assets_year": _field(person, "declared_assets_year"),
                    "salary_reference_year": _field(person, "salary_reference_year"),
                    "salary_reference_source": _field(person, "salary_reference_source"),
                },
            ).to_dict()
        )

    return alerts


def check_incestuous_relationships(
    connection: Neo4jConnection | None = None,
) -> list[dict[str, Any]]:
    graph = connection or neo4j_connection
    rows = graph.execute_query(
        """
        MATCH (company:Company)-[:SUPPLIES]->(org:Organization)<-[:OCCUPIES|SIGNED*1..2]-(person:Person)
        OPTIONAL MATCH (company)-[:PARTNER_IS]->(partner)
        WITH company, org, person, partner,
             toLower(coalesce(company.address, company.city, '')) AS company_address,
             toLower(coalesce(person.address, '')) AS person_address,
             split(toLower(coalesce(person.full_name, '')), ' ')[-1] AS person_surname,
             split(toLower(coalesce(partner.name, partner.partner_name, '')), ' ')[-1] AS partner_surname
        WHERE (company_address <> '' AND person_address <> '' AND company_address = person_address)
           OR (person_surname <> '' AND partner_surname <> '' AND person_surname = partner_surname)
        RETURN company.id AS company_id,
               company.legal_name AS company_name,
               org.id AS organization_id,
               org.name AS organization_name,
               person.id AS person_id,
               person.full_name AS person_name,
               partner.name AS partner_name
        LIMIT 100
        """
    )
    alerts: list[dict[str, Any]] = []
    for row in rows:
        company_id = row.get("company_id")
        if not company_id:
            continue
        alerts.append(
            RiskAlert(
                entity_type="company",
                entity_id=str(company_id),
                alert_type="incestuous_relationship",
                severity="high",
                score=Decimal("82.000"),
                title="Possivel vinculo familiar ou residencial",
                explanation=(
                    "Fornecedor contratado possui indicio de sobrenome ou endereco "
                    "compartilhado com agente publico relacionado ao orgao."
                ),
                evidence=row,
            ).to_dict()
        )
    return alerts


def _entity_id(entity: Any, field: str) -> str:
    value = _field(entity, field)
    if value is None:
        return ""
    if isinstance(value, UUID):
        return str(value)
    return str(value)


def _date_value(entity: Any, field: str) -> date | None:
    value = _field(entity, field)
    return value if isinstance(value, date) else None


def _decimal_value(entity: Any, field: str) -> Decimal:
    value = _field(entity, field)
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _field(entity: Any, field: str) -> Any:
    if isinstance(entity, dict):
        return entity.get(field)
    return getattr(entity, field, None)


def _score(multiplier: Decimal, base: int) -> Decimal:
    raw_score = Decimal(base) + ((multiplier - Decimal("1")) * Decimal("20"))
    return max(Decimal("0"), min(Decimal("100"), raw_score.quantize(Decimal("0.001"))))


def _severity(multiplier: Decimal) -> str:
    if multiplier >= Decimal("2"):
        return "critical"
    if multiplier >= Decimal("1.5"):
        return "high"
    if multiplier >= Decimal("1"):
        return "medium"
    return "low"
