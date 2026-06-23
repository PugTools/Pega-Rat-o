from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import nullslast
from sqlalchemy.orm import Session

from app.core.cache import get_json_cache, set_json_cache
from app.db.database import get_db
from app.db.models import Person
from app.schemas.core_schemas import PersonResponse


router = APIRouter(prefix="/persons", tags=["persons"])


@router.get("", response_model=list[PersonResponse])
def list_persons(
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    name: str | None = None,
    masked_cpf: str | None = None,
    party: str | None = None,
    state_code: str | None = None,
    order_by: str = Query(default="expense_total", pattern="^(expense_total|name|party|state)$"),
) -> list[Person] | list[dict]:
    cache_key = (
        "persons:"
        f"{skip}:{limit}:{name or ''}:{masked_cpf or ''}:"
        f"{party or ''}:{state_code or ''}:{order_by}"
    )
    cached = get_json_cache(cache_key)
    if cached is not None:
        return cached

    query = db.query(Person)

    if name:
        query = query.filter(Person.normalized_name.ilike(f"%{name.lower()}%"))
    if masked_cpf:
        query = query.filter(Person.masked_cpf == masked_cpf)
    if party:
        query = query.filter(Person.party_acronym == party.upper())
    if state_code:
        query = query.filter(Person.state_code == state_code.upper())

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


@router.get("/{person_id}", response_model=PersonResponse)
def get_person(person_id: UUID, db: Session = Depends(get_db)) -> Person | dict:
    cache_key = f"persons:detail:{person_id}"
    cached = get_json_cache(cache_key)
    if cached is not None:
        return cached

    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person not found.",
        )

    payload = PersonResponse.model_validate(person).model_dump(mode="json")
    set_json_cache(cache_key, payload, ttl_seconds=300)
    return payload
