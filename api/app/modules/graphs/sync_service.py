import logging
from typing import Any

from app.db.models import Company, Contract, Organization, Person
from app.db.neo4j_database import Neo4jConnection, neo4j_connection


logger = logging.getLogger(__name__)


class GraphSyncService:
    def __init__(self, connection: Neo4jConnection | None = None) -> None:
        self.connection = connection or neo4j_connection

    def sync_person(self, person: Person) -> None:
        self.connection.execute_query(
            """
            MERGE (p:Person {id: $id})
            SET p.full_name = $full_name,
                p.normalized_name = $normalized_name,
                p.masked_cpf = $masked_cpf,
                p.birth_year = $birth_year,
                p.data_origin = $data_origin,
                p.external_id = $external_id,
                p.party_acronym = $party_acronym,
                p.state_code = $state_code,
                p.photo_url = $photo_url,
                p.email = $email,
                p.latest_expense_total = $latest_expense_total,
                p.latest_expense_year = $latest_expense_year,
                p.updated_at = datetime()
            WITH p
            FOREACH (_ IN CASE WHEN $party_acronym IS NULL THEN [] ELSE [1] END |
                MERGE (party:Party {acronym: $party_acronym})
                SET party.updated_at = datetime()
                MERGE (p)-[:AFFILIATED_TO]->(party)
            )
            WITH p
            FOREACH (_ IN CASE WHEN $state_code IS NULL THEN [] ELSE [1] END |
                MERGE (state:State {code: $state_code})
                SET state.updated_at = datetime()
                MERGE (p)-[:ELECTED_IN]->(state)
            )
            """,
            {
                "id": str(person.id),
                "full_name": person.full_name,
                "normalized_name": person.normalized_name,
                "masked_cpf": person.masked_cpf,
                "birth_year": person.birth_year,
                "data_origin": person.data_origin,
                "external_id": person.external_id,
                "party_acronym": person.party_acronym,
                "state_code": person.state_code,
                "photo_url": person.photo_url,
                "email": person.email,
                "latest_expense_total": (
                    float(person.latest_expense_total)
                    if person.latest_expense_total is not None
                    else None
                ),
                "latest_expense_year": person.latest_expense_year,
            },
            write=True,
        )

    def ensure_constraints(self) -> None:
        if not self.connection.verify():
            logger.warning("neo4j_constraints_skipped_unavailable")
            return

        statements = [
            "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT company_id IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT organization_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE",
            "CREATE CONSTRAINT contract_id IF NOT EXISTS FOR (ct:Contract) REQUIRE ct.id IS UNIQUE",
            "CREATE CONSTRAINT party_acronym IF NOT EXISTS FOR (p:Party) REQUIRE p.acronym IS UNIQUE",
            "CREATE CONSTRAINT state_code IF NOT EXISTS FOR (s:State) REQUIRE s.code IS UNIQUE",
            "CREATE INDEX person_origin_external IF NOT EXISTS FOR (p:Person) ON (p.data_origin, p.external_id)",
            "CREATE INDEX person_party_state IF NOT EXISTS FOR (p:Person) ON (p.party_acronym, p.state_code)",
            "CREATE INDEX cited_entity_name IF NOT EXISTS FOR (e:CitedEntity) ON (e.name)",
        ]
        for statement in statements:
            self.connection.execute_query(statement, write=True)

    def sync_organization(self, organization: Organization) -> None:
        self.connection.execute_query(
            """
            MERGE (o:Organization {id: $id})
            SET o.name = $name,
                o.normalized_name = $normalized_name,
                o.cnpj = $cnpj,
                o.organization_type = $organization_type,
                o.jurisdiction_level = $jurisdiction_level,
                o.state_code = $state_code,
                o.municipality_code = $municipality_code,
                o.updated_at = datetime()
            """,
            {
                "id": str(organization.id),
                "name": organization.name,
                "normalized_name": organization.normalized_name,
                "cnpj": organization.cnpj,
                "organization_type": organization.organization_type,
                "jurisdiction_level": organization.jurisdiction_level,
                "state_code": organization.state_code,
                "municipality_code": organization.municipality_code,
            },
            write=True,
        )

    def sync_company(self, company: Company) -> None:
        self.connection.execute_query(
            """
            MERGE (c:Company {id: $id})
            SET c.legal_name = $legal_name,
                c.trade_name = $trade_name,
                c.cnpj = $cnpj,
                c.cnae = $cnae,
                c.city = $city,
                c.state_code = $state_code,
                c.registration_status = $registration_status,
                c.updated_at = datetime()
            """,
            {
                "id": str(company.id),
                "legal_name": company.legal_name,
                "trade_name": company.trade_name,
                "cnpj": company.cnpj,
                "cnae": company.cnae,
                "city": company.city,
                "state_code": company.state_code,
                "registration_status": company.registration_status,
            },
            write=True,
        )

    def sync_contract(self, contract: Contract) -> None:
        self.connection.execute_query(
            """
            MERGE (ct:Contract {id: $id})
            SET ct.contract_number = $contract_number,
                ct.process_number = $process_number,
                ct.object = $object,
                ct.modality = $modality,
                ct.status = $status,
                ct.total_value = $total_value,
                ct.updated_at = datetime()
            WITH ct
            OPTIONAL MATCH (c:Company {id: $supplier_company_id})
            FOREACH (_ IN CASE WHEN c IS NULL THEN [] ELSE [1] END |
                MERGE (c)-[:AWARDED]->(ct)
            )
            WITH ct
            OPTIONAL MATCH (o:Organization {id: $organization_id})
            FOREACH (_ IN CASE WHEN o IS NULL THEN [] ELSE [1] END |
                MERGE (o)-[:SIGNED]->(ct)
            )
            """,
            {
                "id": str(contract.id),
                "contract_number": contract.contract_number,
                "process_number": contract.process_number,
                "object": contract.object,
                "modality": contract.modality,
                "status": contract.status,
                "total_value": (
                    float(contract.total_value)
                    if contract.total_value is not None
                    else None
                ),
                "supplier_company_id": (
                    str(contract.supplier_company_id)
                    if contract.supplier_company_id
                    else None
                ),
                "organization_id": (
                    str(contract.organization_id) if contract.organization_id else None
                ),
            },
            write=True,
        )

    def sync_contract_relationships(self, contract: Contract) -> None:
        if contract.supplier_company_id and contract.organization_id:
            self.connection.execute_query(
                """
                MATCH (c:Company {id: $company_id})
                MATCH (o:Organization {id: $organization_id})
                MERGE (c)-[r:SUPPLIES]->(o)
                SET r.last_seen_at = datetime()
                """,
                {
                    "company_id": str(contract.supplier_company_id),
                    "organization_id": str(contract.organization_id),
                },
                write=True,
            )

    def sync_contracts(self, contracts: list[Contract]) -> None:
        for contract in contracts:
            self.sync_related_entities(contract)
            self.sync_contract(contract)
            self.sync_contract_relationships(contract)

    def sync_related_entities(self, contract: Contract) -> None:
        if contract.supplier is not None:
            self.sync_company(contract.supplier)
        if contract.organization is not None:
            self.sync_organization(contract.organization)

    def sync_cited_entity(
        self,
        name: str,
        entity_label: str,
        source_entity_type: str,
        source_entity_id: str,
    ) -> None:
        self.connection.execute_query(
            """
            MERGE (e:CitedEntity {name: $name, label: $label})
            SET e.updated_at = datetime()
            WITH e
            MATCH (source {id: $source_entity_id})
            WHERE $source_entity_type IN labels(source)
            MERGE (source)-[:MENTIONS]->(e)
            """,
            {
                "name": name,
                "label": entity_label,
                "source_entity_type": source_entity_type,
                "source_entity_id": source_entity_id,
            },
            write=True,
        )

    def get_entity_neighborhood(
        self,
        entity_type: str,
        entity_id: str,
        depth: int = 2,
    ) -> dict[str, list[dict[str, Any]]]:
        label = _safe_label(entity_type)
        safe_entity_id = _safe_entity_id(entity_id)
        if label is None or safe_entity_id is None:
            return {"nodes": [], "edges": []}

        rows = self.connection.execute_query(
            _neighborhood_query(depth),
            {"entity_id": safe_entity_id, "label": label},
        )

        if not rows:
            return {"nodes": [], "edges": []}

        return {
            "nodes": rows[0].get("nodes", []),
            "edges": rows[0].get("edges", []),
        }


def _safe_label(entity_type: str) -> str | None:
    labels = {
        "company": "Company",
        "companies": "Company",
        "organization": "Organization",
        "organizations": "Organization",
        "contract": "Contract",
        "contracts": "Contract",
        "person": "Person",
        "persons": "Person",
        "party": "Party",
        "parties": "Party",
        "state": "State",
        "states": "State",
        "citedentity": "CitedEntity",
        "citedentities": "CitedEntity",
    }
    return labels.get(entity_type.lower())


def _safe_entity_id(entity_id: str) -> str | None:
    value = str(entity_id or "").strip()
    if not value or len(value) > 160:
        return None
    return value


def _neighborhood_query(depth: int) -> str:
    if depth <= 1:
        return """
        MATCH (root {id: $entity_id})
        WHERE $label IN labels(root)
        MATCH path = (root)-[*0..1]-(neighbor)
        WITH collect(path) AS paths
        CALL {
            WITH paths
            UNWIND paths AS p
            UNWIND nodes(p) AS n
            RETURN collect(DISTINCT n) AS ns
        }
        CALL {
            WITH paths
            UNWIND paths AS p
            UNWIND relationships(p) AS r
            RETURN collect(DISTINCT r) AS rs
        }
        RETURN
            [n IN ns | {
                id: n.id,
                label: labels(n)[0],
                properties: properties(n)
            }] AS nodes,
            [r IN rs | {
                id: elementId(r),
                source: startNode(r).id,
                target: endNode(r).id,
                type: type(r),
                properties: properties(r)
            }] AS edges
        """
    return """
    MATCH (root {id: $entity_id})
    WHERE $label IN labels(root)
    MATCH path = (root)-[*0..2]-(neighbor)
    WITH collect(path) AS paths
    CALL {
        WITH paths
        UNWIND paths AS p
        UNWIND nodes(p) AS n
        RETURN collect(DISTINCT n) AS ns
    }
    CALL {
        WITH paths
        UNWIND paths AS p
        UNWIND relationships(p) AS r
        RETURN collect(DISTINCT r) AS rs
    }
    RETURN
        [n IN ns | {
            id: n.id,
            label: labels(n)[0],
            properties: properties(n)
        }] AS nodes,
        [r IN rs | {
            id: elementId(r),
            source: startNode(r).id,
            target: endNode(r).id,
            type: type(r),
            properties: properties(r)
        }] AS edges
    """
