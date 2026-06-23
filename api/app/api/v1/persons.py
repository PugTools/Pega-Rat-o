from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import nullslast
from sqlalchemy.orm import Session, selectinload

from app.core.cache import get_json_cache, set_json_cache
from app.db.database import get_db
from app.db.models import Expense, Person, PublicRole
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
    expenses = (
        db.query(Expense)
        .filter(Expense.person_id == person_id)
        .order_by(Expense.expense_date.desc(), Expense.created_at.desc())
        .limit(25)
        .all()
    )
    payload["recent_expenses"] = [
        ExpenseResponse.model_validate(expense).model_dump(mode="json")
        for expense in expenses
    ]
    payload["expense_total"] = str(
        sum((expense.amount or 0) for expense in expenses)
    )
    set_json_cache(cache_key, payload, ttl_seconds=300)
    return payload
