from decimal import Decimal
from hashlib import sha256
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Company,
    Contract,
    Expense,
    Organization,
    Person,
    PublicRole,
    RawDocument,
    RiskAlert as RiskAlertModel,
)
from app.modules.alerts.risk_rules import RiskAlert
from app.schemas.core_schemas import (
    CompanyCreate,
    ContractCreate,
    ExpenseCreate,
    OrganizationCreate,
    PersonCreate,
    PublicRoleCreate,
)


def create_person(db: Session, payload: PersonCreate) -> Person:
    person = Person(**payload.model_dump())
    db.add(person)
    db.flush()
    return person


def upsert_person(db: Session, payload: PersonCreate) -> Person:
    data = payload.model_dump()
    masked_cpf = data.get("masked_cpf")
    external_id = data.get("external_id")
    data_origin = data.get("data_origin")
    person = None

    if external_id and data_origin:
        person = db.scalar(
            select(Person)
            .where(Person.external_id == external_id)
            .where(Person.data_origin == data_origin)
        )

    if person is None and masked_cpf:
        person = db.scalar(select(Person).where(Person.masked_cpf == masked_cpf))

    if person is None and data.get("normalized_name"):
        query = select(Person).where(Person.normalized_name == data["normalized_name"])
        if data.get("state_code"):
            query = query.where(Person.state_code == data["state_code"])
        person = db.scalar(query)

    if person is None:
        person = Person(**data)
        db.add(person)
    else:
        _apply_updates(person, data)

    db.flush()
    return person


def upsert_public_role(db: Session, payload: PublicRoleCreate) -> PublicRole:
    data = payload.model_dump()
    role = db.scalar(
        select(PublicRole)
        .where(PublicRole.person_id == data["person_id"])
        .where(PublicRole.role_name == data["role_name"])
        .where(PublicRole.jurisdiction_level == data.get("jurisdiction_level"))
        .where(PublicRole.state_code == data.get("state_code"))
    )

    if role is None:
        role = PublicRole(**data)
        db.add(role)
    else:
        _apply_updates(role, data)

    db.flush()
    return role


def create_organization(db: Session, payload: OrganizationCreate) -> Organization:
    organization = Organization(**payload.model_dump())
    db.add(organization)
    db.flush()
    return organization


def upsert_organization(db: Session, payload: OrganizationCreate) -> Organization:
    data = payload.model_dump()
    cnpj = data.get("cnpj")
    normalized_name = data.get("normalized_name")
    organization = None

    if cnpj:
        organization = db.scalar(select(Organization).where(Organization.cnpj == cnpj))
    if organization is None and normalized_name:
        query = select(Organization).where(Organization.normalized_name == normalized_name)
        state_code = data.get("state_code")
        municipality_code = data.get("municipality_code")
        if state_code:
            query = query.where(Organization.state_code == state_code)
        if municipality_code:
            query = query.where(Organization.municipality_code == municipality_code)
        organization = db.scalar(query)

    if organization is None:
        organization = Organization(**data)
        db.add(organization)
    else:
        _apply_updates(organization, data)

    db.flush()
    return organization


def create_company(db: Session, payload: CompanyCreate) -> Company:
    company = Company(**payload.model_dump())
    db.add(company)
    db.flush()
    return company


def upsert_company(db: Session, payload: CompanyCreate) -> Company:
    data = payload.model_dump()
    company = db.scalar(select(Company).where(Company.cnpj == data["cnpj"]))

    if company is None:
        company = Company(**data)
        db.add(company)
    else:
        _apply_updates(company, data)

    db.flush()
    return company


def create_contract(db: Session, payload: ContractCreate) -> Contract:
    contract = Contract(**payload.model_dump())
    db.add(contract)
    db.flush()
    return contract


def upsert_contract(db: Session, payload: ContractCreate) -> Contract:
    data = payload.model_dump()
    contract = _find_existing_contract(db, data)

    if contract is None:
        contract = Contract(**data)
        db.add(contract)
    else:
        _apply_updates(contract, data)

    db.flush()
    return contract


def create_expense(db: Session, payload: ExpenseCreate) -> Expense:
    data = _prepare_expense_data(db, payload)
    expense = Expense(**data)
    db.add(expense)
    db.flush()
    return expense


def upsert_expense(db: Session, payload: ExpenseCreate) -> Expense:
    data = _prepare_expense_data(db, payload)
    expense = _find_existing_expense(db, data)

    if expense is None:
        expense = Expense(**data)
        db.add(expense)
    else:
        _apply_updates(expense, data)

    db.flush()
    return expense


def upsert_raw_document(
    db: Session,
    document_url: str,
    source_id: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> RawDocument:
    document_hash = sha256(document_url.encode("utf-8")).hexdigest()
    raw_document = db.scalar(
        select(RawDocument).where(RawDocument.sha256 == document_hash)
    )
    payload = {
        "source_id": source_id,
        "original_url": document_url,
        "storage_uri": document_url,
        "mime_type": None,
        "sha256": document_hash,
        "metadata_json": {
            "official_url": document_url,
            "document_url": document_url,
            **(metadata or {}),
        },
    }

    if raw_document is None:
        raw_document = RawDocument(**payload)
        db.add(raw_document)
    else:
        _apply_updates(raw_document, payload)

    db.flush()
    return raw_document


def save_alerts(
    db: Session,
    alerts: list[RiskAlert | dict[str, Any]],
) -> list[RiskAlertModel]:
    saved: list[RiskAlertModel] = []

    for alert in alerts:
        data = _alert_to_dict(alert)
        if not data:
            continue

        entity_id = _coerce_uuid(data["entity_id"])
        payload = {
            "entity_type": data["entity_type"],
            "entity_id": entity_id,
            "alert_type": data["alert_type"],
            "severity": data["severity"],
            "score": Decimal(str(data["score"])),
            "title": data["title"],
            "explanation": data["explanation"],
            "evidence": data.get("evidence") or {},
            "status": data.get("status", "open"),
        }

        risk_alert = db.scalar(
            select(RiskAlertModel)
            .where(RiskAlertModel.entity_type == payload["entity_type"])
            .where(RiskAlertModel.entity_id == payload["entity_id"])
            .where(RiskAlertModel.alert_type == payload["alert_type"])
            .where(RiskAlertModel.status == payload["status"])
        )

        if risk_alert is None:
            risk_alert = RiskAlertModel(**payload)
            db.add(risk_alert)
        else:
            _apply_updates(risk_alert, payload)

        saved.append(risk_alert)

    db.flush()
    return saved


def _find_existing_contract(db: Session, data: dict) -> Contract | None:
    contract_number = data.get("contract_number")
    process_number = data.get("process_number")
    organization_id = data.get("organization_id")

    if contract_number:
        query = select(Contract).where(Contract.contract_number == contract_number)
        if organization_id:
            query = query.where(Contract.organization_id == organization_id)
        contract = db.scalar(query)
        if contract:
            return contract

    if process_number:
        query = select(Contract).where(Contract.process_number == process_number)
        if organization_id:
            query = query.where(Contract.organization_id == organization_id)
        return db.scalar(query)

    return None


def _find_existing_expense(db: Session, data: dict) -> Expense | None:
    commitment_number = data.get("commitment_number")
    payment_number = data.get("payment_number")
    liquidation_number = data.get("liquidation_number")
    organization_id = data.get("organization_id")
    person_id = data.get("person_id")

    for field_name, model_field in (
        ("payment_number", Expense.payment_number),
        ("liquidation_number", Expense.liquidation_number),
        ("commitment_number", Expense.commitment_number),
    ):
        value = data.get(field_name)
        if not value:
            continue

        query = select(Expense).where(model_field == value)
        if organization_id:
            query = query.where(Expense.organization_id == organization_id)
        if person_id:
            query = query.where(Expense.person_id == person_id)
        expense = db.scalar(query)
        if expense:
            return expense

    if not (commitment_number or payment_number or liquidation_number):
        query = (
            select(Expense)
            .where(Expense.amount == data["amount"])
            .where(Expense.expense_date == data["expense_date"])
            .where(Expense.description == data.get("description"))
        )
        if organization_id:
            query = query.where(Expense.organization_id == organization_id)
        if person_id:
            query = query.where(Expense.person_id == person_id)
        company_id: UUID | None = data.get("company_id")
        if company_id:
            query = query.where(Expense.company_id == company_id)
        return db.scalar(query)

    return None


def _prepare_expense_data(db: Session, payload: ExpenseCreate) -> dict[str, Any]:
    data = payload.model_dump()
    data.pop("supplier_payload", None)
    data.pop("document_url", None)

    supplier_payload = getattr(payload, "supplier_payload", None)
    if supplier_payload is not None and not data.get("company_id"):
        company = upsert_company(db, supplier_payload)
        data["company_id"] = company.id

    document_url = getattr(payload, "document_url", None)
    if document_url and not data.get("raw_document_id"):
        raw_document = upsert_raw_document(
            db,
            document_url=document_url,
            source_id=data.get("source_id"),
        )
        data["raw_document_id"] = raw_document.id

    return data


def _apply_updates(instance: object, data: dict) -> None:
    for field, value in data.items():
        if value is not None:
            setattr(instance, field, value)


def _alert_to_dict(alert: Any) -> dict[str, Any]:
    if isinstance(alert, dict):
        return alert
    if hasattr(alert, "to_dict"):
        return alert.to_dict()
    return {}


def _coerce_uuid(value: Any) -> UUID:
    if isinstance(value, UUID):
        return value
    text_value = str(value)
    try:
        return UUID(text_value)
    except ValueError:
        return uuid5(NAMESPACE_URL, text_value)
