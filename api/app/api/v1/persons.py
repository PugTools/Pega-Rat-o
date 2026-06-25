from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import nullslast
from sqlalchemy.orm import Session, selectinload

from app.core.cache import get_json_cache, set_json_cache
from app.db.database import get_db
from app.db.models import Company, Expense, Person, PublicRole, RawDocument
from app.schemas.core_schemas import ExpenseResponse, PersonDetailResponse, PersonResponse


router = APIRouter(prefix="/persons", tags=["persons"])


@router.get("", response_model=list[PersonResponse])
def list_persons(
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=1000),
    name: str | None = None,
    masked_cpf: str | None = None,
    party: str | None = None,
    state_code: str | None = None,
    role_name: str | None = None,
    jurisdiction_level: str | None = None,
    municipality_code: str | None = None,
    order_by: str = Query(default="expense_total", pattern="^(expense_total|name|party|state)$"),
) -> list[Person] | list[dict]:
    cache_key = (
        "persons:"
        f"{skip}:{limit}:{name or ''}:{masked_cpf or ''}:"
        f"{party or ''}:{state_code or ''}:{role_name or ''}:"
        f"{jurisdiction_level or ''}:{municipality_code or ''}:{order_by}"
    )
    cached = get_json_cache(cache_key)
    if cached is not None:
        return cached

    query = db.query(Person).options(selectinload(Person.roles))

    if name:
        query = query.filter(Person.normalized_name.ilike(f"%{name.lower()}%"))
    if masked_cpf:
        query = query.filter(Person.masked_cpf == masked_cpf)
    if party:
        query = query.filter(Person.party_acronym == party.upper())
    if state_code:
        query = query.filter(Person.state_code == state_code.upper())
    if role_name or jurisdiction_level or municipality_code:
        query = query.join(Person.roles)
        if role_name:
            query = query.filter(PublicRole.role_name.ilike(f"%{role_name}%"))
        if jurisdiction_level:
            query = query.filter(PublicRole.jurisdiction_level == jurisdiction_level)
        if municipality_code:
            query = query.filter(PublicRole.municipality_code == municipality_code)
        query = query.distinct()

    if order_by == "expense_total":
        query = query.order_by(nullslast(Person.latest_expense_total.desc()), Person.full_name)
    elif order_by == "party":
        query = query.order_by(nullslast(Person.party_acronym), Person.full_name)
    elif order_by == "state":
        query = query.order_by(nullslast(Person.state_code), Person.full_name)
    else:
        query = query.order_by(Person.full_name)

    persons = query.offset(skip).limit(limit).all()
    payload = [
        PersonResponse.model_validate(person).model_dump(mode="json")
        for person in persons
    ]
    set_json_cache(cache_key, payload, ttl_seconds=300)
    return payload


@router.get("/{person_id}", response_model=PersonDetailResponse)
def get_person(person_id: UUID, db: Session = Depends(get_db)) -> dict:
    cache_key = f"persons:detail:{person_id}"
    cached = get_json_cache(cache_key)
    if cached is not None:
        return cached

    person = (
        db.query(Person)
        .options(selectinload(Person.roles))
        .filter(Person.id == person_id)
        .one_or_none()
    )
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found.",
        )

    payload = PersonResponse.model_validate(person).model_dump(mode="json")
    expense_rows = _query_person_expense_rows(db, person_id=person_id, limit=25)
    payload["recent_expenses"] = [_expense_payload(*row) for row in expense_rows]
    payload["expense_total"] = str(
        sum((expense.amount or 0) for expense, _, _ in expense_rows)
    )
    set_json_cache(cache_key, payload, ttl_seconds=300)
    return payload


@router.get("/{person_id}/expenses", response_model=list[ExpenseResponse])
def list_person_expenses(
    person_id: UUID,
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict]:
    cache_key = f"persons:expenses:{person_id}:{skip}:{limit}"
    cached = get_json_cache(cache_key)
    if cached is not None:
        return cached

    person_exists = db.query(Person.id).filter(Person.id == person_id).one_or_none()
    if person_exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found.",
        )

    rows = _query_person_expense_rows(
        db,
        person_id=person_id,
        skip=skip,
        limit=limit,
    )
    payload = [_expense_payload(*row) for row in rows]
    set_json_cache(cache_key, payload, ttl_seconds=300)
    return payload


def _query_person_expense_rows(
    db: Session,
    person_id: UUID,
    skip: int = 0,
    limit: int = 25,
) -> list[tuple[Expense, Company | None, RawDocument | None]]:
    return (
        db.query(Expense, Company, RawDocument)
        .outerjoin(Company, Expense.company_id == Company.id)
        .outerjoin(RawDocument, Expense.raw_document_id == RawDocument.id)
        .filter(Expense.person_id == person_id)
        .order_by(Expense.expense_date.desc(), Expense.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def _expense_payload(
    expense: Expense,
    supplier: Company | None,
    raw_document: RawDocument | None,
) -> dict:
    payload = ExpenseResponse.model_validate(expense).model_dump(mode="json")
    payload["supplier_company_id"] = str(supplier.id) if supplier else (
        str(expense.company_id) if expense.company_id else None
    )
    payload["supplier_name"] = supplier.legal_name if supplier else None
    payload["supplier_cnpj"] = supplier.cnpj if supplier else None
    payload["document_url"] = _document_url(raw_document)
    return payload


def _document_url(raw_document: RawDocument | None) -> str | None:
    if raw_document is None:
        return None

    metadata = raw_document.metadata_json or {}
    for key in ("document_url", "official_url", "url", "source_url"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return raw_document.original_url or raw_document.storage_uri
