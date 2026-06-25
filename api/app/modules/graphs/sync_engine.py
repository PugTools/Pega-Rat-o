import logging
from collections.abc import Iterable, Iterator
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Company, Contract, Expense, Organization, Person, PublicRole
from app.db.neo4j_database import Neo4jConnection, neo4j_connection


logger = logging.getLogger(__name__)


class MassiveGraphSyncEngine:
    def __init__(
        self,
        connection: Neo4jConnection | None = None,
        batch_size: int = 5000,
    ) -> None:
        self.connection = connection or neo4j_connection
        self.batch_size = batch_size

    def ensure_constraints(self) -> None:
        if not self.connection.verify():
            logger.warning("massive_graph_constraints_skipped_unavailable")
            return

        statements = [
            "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT company_id IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE",
            "CREATE INDEX company_cnpj IF NOT EXISTS FOR (c:Company) ON (c.cnpj)",
            "CREATE CONSTRAINT organization_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE",
            "CREATE CONSTRAINT contract_id IF NOT EXISTS FOR (c:Contract) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT public_role_id IF NOT EXISTS FOR (r:PublicRole) REQUIRE r.id IS UNIQUE",
            "CREATE CONSTRAINT document_value IF NOT EXISTS FOR (d:Document) REQUIRE d.value IS UNIQUE",
            "CREATE CONSTRAINT enforcement_id IF NOT EXISTS FOR (a:EnforcementAction) REQUIRE a.id IS UNIQUE",
            "CREATE INDEX person_masked_cpf IF NOT EXISTS FOR (p:Person) ON (p.masked_cpf)",
            "CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.normalized_name)",
            "CREATE INDEX organization_cnpj IF NOT EXISTS FOR (o:Organization) ON (o.cnpj)",
            "CREATE INDEX contract_value IF NOT EXISTS FOR (c:Contract) ON (c.total_value)",
            "CREATE INDEX donation_year IF NOT EXISTS FOR ()-[r:DOOU_PARA]-() ON (r.election_year)",
        ]
        for statement in statements:
            try:
                self.connection.execute_query(statement, write=True)
            except Exception as exc:
                logger.warning(
                    "massive_graph_constraint_failed",
                    extra={
                        "statement": statement,
                        "error": str(exc),
                    },
                )

    def sync_from_postgres(self, db: Session) -> dict[str, int]:
        counters = {
            "persons": self.sync_people(db.query(Person).yield_per(self.batch_size)),
            "companies": self.sync_companies(db.query(Company).yield_per(self.batch_size)),
            "organizations": self.sync_organizations(
                db.query(Organization).yield_per(self.batch_size)
            ),
            "public_roles": self.sync_public_roles(
                db.query(PublicRole).yield_per(self.batch_size)
            ),
            "contracts": self.sync_contracts(db.query(Contract).yield_per(self.batch_size)),
            "expenses": self.sync_expenses(db.query(Expense).yield_per(self.batch_size)),
        }
        return counters

    def sync_people(self, people: Iterable[Person | dict[str, Any]]) -> int:
        return self._execute_batches(
            people,
            self._person_row,
            """
            UNWIND $rows AS row
            MERGE (p:Person {id: row.id})
            SET p.full_name = row.full_name,
                p.normalized_name = row.normalized_name,
                p.masked_cpf = row.masked_cpf,
                p.birth_year = row.birth_year,
                p.data_origin = row.data_origin,
                p.external_id = row.external_id,
                p.party_acronym = row.party_acronym,
                p.state_code = row.state_code,
                p.email = row.email,
                p.latest_expense_total = row.latest_expense_total,
                p.declared_assets_value = row.declared_assets_value,
                p.asset_salary_ratio = row.asset_salary_ratio,
                p.updated_at = datetime()
            WITH p, row
            FOREACH (_ IN CASE WHEN row.masked_cpf IS NULL THEN [] ELSE [1] END |
                MERGE (d:Document {value: row.masked_cpf})
                SET d.kind = 'masked_cpf', d.updated_at = datetime()
                MERGE (p)-[:IDENTIFIED_BY]->(d)
            )
            WITH p, row
            FOREACH (_ IN CASE WHEN row.party_acronym IS NULL THEN [] ELSE [1] END |
                MERGE (party:Party {acronym: row.party_acronym})
                SET party.updated_at = datetime()
                MERGE (p)-[:AFFILIATED_TO]->(party)
            )
            """,
        )

    def sync_companies(self, companies: Iterable[Company | dict[str, Any]]) -> int:
        return self._execute_batches(
            companies,
            self._company_row,
            """
            UNWIND $rows AS row
            MERGE (c:Company {id: row.id})
            SET c.legal_name = row.legal_name,
                c.trade_name = row.trade_name,
                c.cnpj = row.cnpj,
                c.cnae = row.cnae,
                c.city = row.city,
                c.state_code = row.state_code,
                c.registration_status = row.registration_status,
                c.updated_at = datetime()
            WITH c, row
            FOREACH (_ IN CASE WHEN row.cnpj IS NULL THEN [] ELSE [1] END |
                MERGE (d:Document {value: row.cnpj})
                SET d.kind = 'cnpj', d.updated_at = datetime()
                MERGE (c)-[:IDENTIFIED_BY]->(d)
            )
            """,
        )

    def sync_organizations(
        self,
        organizations: Iterable[Organization | dict[str, Any]],
    ) -> int:
        return self._execute_batches(
            organizations,
            self._organization_row,
            """
            UNWIND $rows AS row
            MERGE (o:Organization {id: row.id})
            SET o.name = row.name,
                o.normalized_name = row.normalized_name,
                o.cnpj = row.cnpj,
                o.organization_type = row.organization_type,
                o.jurisdiction_level = row.jurisdiction_level,
                o.state_code = row.state_code,
                o.municipality_code = row.municipality_code,
                o.updated_at = datetime()
            """,
        )

    def sync_public_roles(self, roles: Iterable[PublicRole | dict[str, Any]]) -> int:
        return self._execute_batches(
            roles,
            self._public_role_row,
            """
            UNWIND $rows AS row
            MERGE (role:PublicRole {id: row.id})
            SET role.role_name = row.role_name,
                role.branch = row.branch,
                role.jurisdiction_level = row.jurisdiction_level,
                role.state_code = row.state_code,
                role.municipality_code = row.municipality_code,
                role.party_acronym = row.party_acronym,
                role.start_date = row.start_date,
                role.end_date = row.end_date,
                role.updated_at = datetime()
            WITH role, row
            MATCH (p:Person {id: row.person_id})
            MERGE (p)-[:OCCUPIES]->(role)
            WITH role, row
            OPTIONAL MATCH (o:Organization {id: row.organization_id})
            FOREACH (_ IN CASE WHEN o IS NULL THEN [] ELSE [1] END |
                MERGE (role)-[:IN_ORGANIZATION]->(o)
            )
            """,
        )

    def sync_contracts(self, contracts: Iterable[Contract | dict[str, Any]]) -> int:
        return self._execute_batches(
            contracts,
            self._contract_row,
            """
            UNWIND $rows AS row
            MERGE (ct:Contract {id: row.id})
            SET ct.contract_number = row.contract_number,
                ct.process_number = row.process_number,
                ct.object = row.object,
                ct.modality = row.modality,
                ct.status = row.status,
                ct.total_value = row.total_value,
                ct.signed_at = row.signed_at,
                ct.starts_at = row.starts_at,
                ct.ends_at = row.ends_at,
                ct.updated_at = datetime()
            WITH ct, row
            OPTIONAL MATCH (company:Company {id: row.supplier_company_id})
            FOREACH (_ IN CASE WHEN company IS NULL THEN [] ELSE [1] END |
                MERGE (company)-[award:VENCEU_LICITACAO]->(ct)
                SET award.total_value = row.total_value,
                    award.source = 'contracts',
                    award.updated_at = datetime()
                MERGE (company)-[:AWARDED]->(ct)
            )
            WITH ct, row
            OPTIONAL MATCH (org:Organization {id: row.organization_id})
            FOREACH (_ IN CASE WHEN org IS NULL THEN [] ELSE [1] END |
                MERGE (org)-[:CONTRATOU]->(ct)
                MERGE (org)-[:SIGNED]->(ct)
            )
            WITH ct, row
            OPTIONAL MATCH (company:Company {id: row.supplier_company_id})
            OPTIONAL MATCH (org:Organization {id: row.organization_id})
            FOREACH (_ IN CASE WHEN company IS NULL OR org IS NULL THEN [] ELSE [1] END |
                MERGE (company)-[r:SUPPLIES]->(org)
                SET r.last_contract_value = row.total_value,
                    r.last_contract_id = row.id,
                    r.source = 'contracts',
                    r.updated_at = datetime()
            )
            """,
        )

    def sync_expenses(self, expenses: Iterable[Expense | dict[str, Any]]) -> int:
        return self._execute_batches(
            expenses,
            self._expense_row,
            """
            UNWIND $rows AS row
            MERGE (e:Expense {id: row.id})
            SET e.expense_type = row.expense_type,
                e.description = row.description,
                e.commitment_number = row.commitment_number,
                e.amount = row.amount,
                e.expense_date = row.expense_date,
                e.fiscal_year = row.fiscal_year,
                e.state_code = row.state_code,
                e.municipality_code = row.municipality_code,
                e.updated_at = datetime()
            WITH e, row
            OPTIONAL MATCH (person:Person {id: row.person_id})
            FOREACH (_ IN CASE WHEN person IS NULL THEN [] ELSE [1] END |
                MERGE (person)-[:CLAIMED_EXPENSE]->(e)
            )
            WITH e, row
            OPTIONAL MATCH (company:Company {id: row.company_id})
            FOREACH (_ IN CASE WHEN company IS NULL THEN [] ELSE [1] END |
                MERGE (company)-[:RECEIVED_PAYMENT]->(e)
            )
            WITH e, row
            OPTIONAL MATCH (contract:Contract {id: row.contract_id})
            FOREACH (_ IN CASE WHEN contract IS NULL THEN [] ELSE [1] END |
                MERGE (contract)-[:PAID_BY]->(e)
            )
            """,
        )

    def sync_company_partners(self, partners: Iterable[dict[str, Any]]) -> int:
        return self._execute_batches(
            partners,
            self._partner_row,
            """
            UNWIND $rows AS row
            MERGE (partner:Person {id: row.partner_key})
            SET partner.full_name = row.partner_name,
                partner.masked_cpf = row.masked_cpf,
                partner.data_origin = coalesce(row.source, 'company_partners'),
                partner.updated_at = datetime()
            WITH partner, row
            MATCH (company:Company {id: row.company_id})
            MERGE (partner)-[r:SOCIO_DE]->(company)
            SET r.partner_type = row.partner_type,
                r.start_date = row.start_date,
                r.source = row.source,
                r.updated_at = datetime()
            """,
        )

    def sync_campaign_donations(self, donations: Iterable[dict[str, Any]]) -> int:
        return self._execute_batches(
            donations,
            self._donation_row,
            """
            UNWIND $rows AS row
            MERGE (donor:Donor {id: row.donor_key})
            SET donor.name = row.donor_name,
                donor.document = row.donor_document,
                donor.kind = row.donor_kind,
                donor.updated_at = datetime()
            WITH donor, row
            MERGE (candidate:Person {id: row.candidate_key})
            SET candidate.full_name = row.candidate_name,
                candidate.external_id = row.candidate_external_id,
                candidate.party_acronym = row.party_acronym,
                candidate.state_code = row.state_code,
                candidate.data_origin = coalesce(row.source, 'tse_donations'),
                candidate.updated_at = datetime()
            MERGE (donor)-[r:DOOU_PARA {election_year: row.election_year, receipt_id: row.receipt_id}]->(candidate)
            SET r.amount = row.amount,
                r.source = row.source,
                r.updated_at = datetime()
            WITH donor, row
            OPTIONAL MATCH (company:Company {cnpj: row.donor_document})
            FOREACH (_ IN CASE WHEN company IS NULL THEN [] ELSE [1] END |
                MERGE (company)-[:SAME_DOCUMENT_AS]->(donor)
            )
            """,
        )

    def sync_bid_awards(self, awards: Iterable[dict[str, Any]]) -> int:
        return self._execute_batches(
            awards,
            self._award_row,
            """
            UNWIND $rows AS row
            MERGE (bid:Bid {id: row.bid_key})
            SET bid.bid_number = row.bid_number,
                bid.process_number = row.process_number,
                bid.modality = row.modality,
                bid.object = row.object,
                bid.estimated_value = row.estimated_value,
                bid.opening_date = row.opening_date,
                bid.source = row.source,
                bid.updated_at = datetime()
            WITH bid, row
            MATCH (company:Company {id: row.company_id})
            MERGE (company)-[r:VENCEU_LICITACAO]->(bid)
            SET r.amount = row.award_amount,
                r.source = row.source,
                r.updated_at = datetime()
            """,
        )

    def sync_kinships(self, kinships: Iterable[dict[str, Any]]) -> int:
        return self._execute_batches(
            kinships,
            self._kinship_row,
            """
            UNWIND $rows AS row
            MATCH (a:Person {id: row.person_a_id})
            MATCH (b:Person {id: row.person_b_id})
            MERGE (a)-[r:PARENTE_DE]-(b)
            SET r.relationship = row.relationship,
                r.confidence = row.confidence,
                r.evidence = row.evidence,
                r.source = row.source,
                r.updated_at = datetime()
            """,
        )

    def sync_enforcements(self, enforcements: Iterable[dict[str, Any]]) -> int:
        return self._execute_batches(
            enforcements,
            self._enforcement_row,
            """
            UNWIND $rows AS row
            MERGE (action:EnforcementAction {id: row.enforcement_id})
            SET action.process_number = row.process_number,
                action.agency = row.agency,
                action.amount = row.amount,
                action.reason = row.reason,
                action.date = row.date,
                action.source = row.source,
                action.updated_at = datetime()
            WITH action, row
            OPTIONAL MATCH (company:Company {cnpj: row.target_document})
            OPTIONAL MATCH (person:Person {masked_cpf: row.target_document})
            WITH action, row, coalesce(company, person) AS target
            FOREACH (_ IN CASE WHEN target IS NULL THEN [] ELSE [1] END |
                MERGE (target)-[r:AUTUADO_POR]->(action)
                SET r.agency = row.agency,
                    r.amount = row.amount,
                    r.updated_at = datetime()
            )
            """,
        )

    def _execute_batches(
        self,
        items: Iterable[Any],
        row_mapper: Any,
        cypher: str,
    ) -> int:
        total = 0
        for batch in _chunks(items, self.batch_size):
            rows = self._map_rows(batch=batch, row_mapper=row_mapper)
            if not rows:
                continue
            total += self._execute_rows_with_fallback(cypher=cypher, rows=rows)
        return total

    def _map_rows(self, batch: list[Any], row_mapper: Any) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in batch:
            try:
                row = row_mapper(item)
            except Exception as exc:
                logger.warning(
                    "massive_graph_row_mapping_failed",
                    extra={
                        "mapper": getattr(row_mapper, "__name__", str(row_mapper)),
                        "error": str(exc),
                    },
                )
                continue
            if row:
                rows.append(self._sanitize_row(row))
        return rows

    def _execute_rows_with_fallback(
        self,
        cypher: str,
        rows: list[dict[str, Any]],
        depth: int = 0,
    ) -> int:
        if not rows:
            return 0

        try:
            self.connection.execute_query(cypher, {"rows": rows}, write=True)
            return len(rows)
        except Exception as exc:
            logger.warning(
                "massive_graph_batch_failed",
                extra={
                    "rows": len(rows),
                    "depth": depth,
                    "error": str(exc),
                },
            )

        if len(rows) == 1:
            logger.error(
                "massive_graph_row_skipped",
                extra={
                    "row": rows[0],
                    "reason": "neo4j_batch_failed_after_isolation",
                },
            )
            return 0

        midpoint = max(1, len(rows) // 2)
        return self._execute_rows_with_fallback(
            cypher=cypher,
            rows=rows[:midpoint],
            depth=depth + 1,
        ) + self._execute_rows_with_fallback(
            cypher=cypher,
            rows=rows[midpoint:],
            depth=depth + 1,
        )

    def _sanitize_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            str(key): _safe_neo4j_value(value)
            for key, value in row.items()
            if key is not None
        }

    def _person_row(self, item: Person | dict[str, Any]) -> dict[str, Any]:
        person_id = _string(_field(item, "id") or _field(item, "person_id"))
        if not person_id:
            return {}
        return {
            "id": person_id,
            "full_name": _field(item, "full_name"),
            "normalized_name": _field(item, "normalized_name"),
            "masked_cpf": _field(item, "masked_cpf"),
            "birth_year": _field(item, "birth_year"),
            "data_origin": _field(item, "data_origin"),
            "external_id": _field(item, "external_id"),
            "party_acronym": _field(item, "party_acronym"),
            "state_code": _field(item, "state_code"),
            "email": _field(item, "email"),
            "latest_expense_total": _float(_field(item, "latest_expense_total")),
            "declared_assets_value": _float(_field(item, "declared_assets_value")),
            "asset_salary_ratio": _float(_field(item, "asset_salary_ratio")),
        }

    def _company_row(self, item: Company | dict[str, Any]) -> dict[str, Any]:
        cnpj = _digits(_field(item, "cnpj"))
        company_id = _string(_field(item, "id") or cnpj)
        if not company_id:
            return {}
        return {
            "id": company_id,
            "legal_name": _field(item, "legal_name"),
            "trade_name": _field(item, "trade_name"),
            "cnpj": cnpj,
            "cnae": _field(item, "cnae"),
            "city": _field(item, "city"),
            "state_code": _field(item, "state_code"),
            "registration_status": _field(item, "registration_status"),
        }

    def _organization_row(self, item: Organization | dict[str, Any]) -> dict[str, Any]:
        organization_id = _string(_field(item, "id") or _field(item, "cnpj") or _field(item, "name"))
        if not organization_id:
            return {}
        return {
            "id": organization_id,
            "name": _field(item, "name"),
            "normalized_name": _field(item, "normalized_name"),
            "cnpj": _digits(_field(item, "cnpj")),
            "organization_type": _field(item, "organization_type"),
            "jurisdiction_level": _field(item, "jurisdiction_level"),
            "state_code": _field(item, "state_code"),
            "municipality_code": _field(item, "municipality_code"),
        }

    def _public_role_row(self, item: PublicRole | dict[str, Any]) -> dict[str, Any]:
        role_id = _string(_field(item, "id"))
        person_id = _string(_field(item, "person_id"))
        if not role_id or not person_id:
            return {}
        return {
            "id": role_id,
            "person_id": person_id,
            "role_name": _field(item, "role_name"),
            "branch": _field(item, "branch"),
            "jurisdiction_level": _field(item, "jurisdiction_level"),
            "state_code": _field(item, "state_code"),
            "municipality_code": _field(item, "municipality_code"),
            "party_acronym": _field(item, "party_acronym"),
            "organization_id": _string(_field(item, "organization_id")),
            "start_date": _iso_date(_field(item, "start_date")),
            "end_date": _iso_date(_field(item, "end_date")),
        }

    def _contract_row(self, item: Contract | dict[str, Any]) -> dict[str, Any]:
        contract_id = _string(_field(item, "id"))
        if not contract_id:
            return {}
        return {
            "id": contract_id,
            "contract_number": _field(item, "contract_number"),
            "process_number": _field(item, "process_number"),
            "organization_id": _string(_field(item, "organization_id")),
            "supplier_company_id": _string(_field(item, "supplier_company_id")),
            "object": _field(item, "object"),
            "modality": _field(item, "modality"),
            "status": _field(item, "status"),
            "signed_at": _iso_date(_field(item, "signed_at")),
            "starts_at": _iso_date(_field(item, "starts_at")),
            "ends_at": _iso_date(_field(item, "ends_at")),
            "total_value": _float(_field(item, "total_value")),
        }

    def _expense_row(self, item: Expense | dict[str, Any]) -> dict[str, Any]:
        expense_id = _string(_field(item, "id"))
        if not expense_id:
            return {}
        return {
            "id": expense_id,
            "person_id": _string(_field(item, "person_id")),
            "company_id": _string(_field(item, "company_id")),
            "contract_id": _string(_field(item, "contract_id")),
            "expense_type": _field(item, "expense_type"),
            "description": _field(item, "description"),
            "commitment_number": _field(item, "commitment_number"),
            "amount": _float(_field(item, "amount")),
            "expense_date": _iso_date(_field(item, "expense_date")),
            "fiscal_year": _field(item, "fiscal_year"),
            "state_code": _field(item, "state_code"),
            "municipality_code": _field(item, "municipality_code"),
        }

    def _partner_row(self, item: dict[str, Any]) -> dict[str, Any]:
        partner_key = _string(
            item.get("partner_id")
            or item.get("masked_cpf")
            or item.get("partner_document")
            or item.get("partner_name")
        )
        company_id = _string(item.get("company_id"))
        if not partner_key or not company_id:
            return {}
        return {
            "partner_key": partner_key,
            "partner_name": item.get("partner_name"),
            "masked_cpf": item.get("masked_cpf"),
            "company_id": company_id,
            "partner_type": item.get("partner_type"),
            "start_date": _iso_date(item.get("start_date")),
            "source": item.get("source"),
        }

    def _donation_row(self, item: dict[str, Any]) -> dict[str, Any]:
        donor_document = _digits(item.get("donor_document") or item.get("donor_cnpj"))
        candidate_key = _string(
            item.get("candidate_id")
            or item.get("candidate_external_id")
            or item.get("candidate_name")
        )
        donor_key = _string(item.get("donor_id") or donor_document or item.get("donor_name"))
        if not donor_key or not candidate_key:
            return {}
        receipt_id = _string(item.get("receipt_id") or item.get("document_number"))
        if not receipt_id:
            receipt_id = f"{donor_key}:{candidate_key}:{item.get('election_year')}:{item.get('amount')}"
        return {
            "donor_key": donor_key,
            "donor_name": item.get("donor_name"),
            "donor_document": donor_document,
            "donor_kind": item.get("donor_kind") or ("company" if donor_document and len(donor_document) == 14 else "person"),
            "candidate_key": candidate_key,
            "candidate_name": item.get("candidate_name"),
            "candidate_external_id": item.get("candidate_external_id"),
            "party_acronym": item.get("party_acronym"),
            "state_code": item.get("state_code"),
            "election_year": item.get("election_year"),
            "receipt_id": receipt_id,
            "amount": _float(item.get("amount")),
            "source": item.get("source") or "tse",
        }

    def _award_row(self, item: dict[str, Any]) -> dict[str, Any]:
        bid_key = _string(item.get("bid_id") or item.get("bid_number") or item.get("process_number"))
        company_id = _string(item.get("company_id"))
        if not bid_key or not company_id:
            return {}
        return {
            "bid_key": bid_key,
            "bid_number": item.get("bid_number"),
            "process_number": item.get("process_number"),
            "modality": item.get("modality"),
            "object": item.get("object"),
            "estimated_value": _float(item.get("estimated_value")),
            "opening_date": _iso_date(item.get("opening_date")),
            "company_id": company_id,
            "award_amount": _float(item.get("award_amount") or item.get("amount")),
            "source": item.get("source"),
        }

    def _kinship_row(self, item: dict[str, Any]) -> dict[str, Any]:
        person_a_id = _string(item.get("person_a_id"))
        person_b_id = _string(item.get("person_b_id"))
        if not person_a_id or not person_b_id:
            return {}
        return {
            "person_a_id": person_a_id,
            "person_b_id": person_b_id,
            "relationship": item.get("relationship"),
            "confidence": _float(item.get("confidence")) or 1.0,
            "evidence": item.get("evidence") or {},
            "source": item.get("source"),
        }

    def _enforcement_row(self, item: dict[str, Any]) -> dict[str, Any]:
        enforcement_id = _string(item.get("id") or item.get("process_number"))
        if not enforcement_id:
            return {}
        return {
            "enforcement_id": enforcement_id,
            "process_number": item.get("process_number"),
            "agency": item.get("agency"),
            "amount": _float(item.get("amount")),
            "reason": item.get("reason"),
            "date": _iso_date(item.get("date")),
            "target_document": _digits(item.get("target_document")),
            "source": item.get("source"),
        }


def _chunks(items: Iterable[Any], size: int) -> Iterator[list[Any]]:
    batch: list[Any] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def _field(item: Any, name: str) -> Any:
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)


def _string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return str(value)
    text = str(value).strip()
    return text or None


def _digits(value: Any) -> str | None:
    text = _string(value)
    if not text:
        return None
    digits = "".join(char for char in text if char.isdigit())
    return digits or None


def _float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _iso_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime | date):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def _safe_neo4j_value(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, dict):
        return {
            str(key): _safe_neo4j_value(nested_value)
            for key, nested_value in value.items()
            if key is not None
        }
    if isinstance(value, list | tuple | set):
        return [_safe_neo4j_value(item) for item in value]
    return str(value)
