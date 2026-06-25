from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.db.database import get_db
from app.db.elasticsearch_db import es_client
from app.db.models import Company, Person


router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def search(
    q: str = Query(min_length=2),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    items = _postgres_search(db=db, q=q, limit=limit)
    elastic_items = _elastic_search(q=q, limit=limit)

    seen = {(item["entity_type"], item["id"]) for item in items}
    for item in elastic_items:
        key = (item["entity_type"], item["id"])
        if key in seen:
            continue
        items.append(item)
        seen.add(key)
        if len(items) >= limit:
            break

    return {
        "query": q,
        "total": len(items),
        "items": items[:limit],
    }


def _postgres_search(db: Session, q: str, limit: int) -> list[dict[str, Any]]:
    normalized_query = q.strip().lower()
    digits = "".join(char for char in q if char.isdigit())
    people_limit = max(3, limit // 2)
    companies_limit = max(3, limit - people_limit)

    people_query = db.query(Person).options(selectinload(Person.roles)).filter(
        or_(
            Person.full_name.ilike(f"%{q}%"),
            Person.normalized_name.ilike(f"%{normalized_query}%"),
            Person.masked_cpf.ilike(f"%{q}%"),
            Person.party_acronym.ilike(f"%{q}%"),
        )
    )
    people = people_query.order_by(Person.full_name).limit(people_limit).all()

    company_filters = [
        Company.legal_name.ilike(f"%{q}%"),
        Company.trade_name.ilike(f"%{q}%"),
    ]
    if digits:
        company_filters.append(Company.cnpj.ilike(f"%{digits}%"))

    companies = (
        db.query(Company)
        .filter(or_(*company_filters))
        .order_by(Company.legal_name)
        .limit(companies_limit)
        .all()
    )

    items: list[dict[str, Any]] = []
    items.extend(
        {
            "id": str(person.id),
            "entity_type": "person",
            "label": person.full_name,
            "subtitle": " / ".join(
                part
                for part in (
                    person.party_acronym,
                    person.state_code,
                    person.roles[0].role_name if person.roles else None,
                )
                if part
            )
            or "Pessoa monitorada",
            "href": f"/politicos/{person.id}",
            "score": 1.0,
            "source": {
                "party_acronym": person.party_acronym,
                "state_code": person.state_code,
                "data_origin": person.data_origin,
                "masked_cpf": person.masked_cpf,
            },
        }
        for person in people
    )
    items.extend(
        {
            "id": str(company.id),
            "entity_type": "company",
            "label": company.legal_name,
            "subtitle": company.cnpj,
            "href": f"/empresas/{company.id}",
            "score": 1.0,
            "source": {
                "cnpj": company.cnpj,
                "trade_name": company.trade_name,
                "state_code": company.state_code,
            },
        }
        for company in companies
    )
    return items


def _elastic_search(q: str, limit: int) -> list[dict[str, Any]]:
    try:
        response = es_client.search(
            index="ongp_persons,ongp_companies,ongp_contracts",
            size=limit,
            query={
                "multi_match": {
                    "query": q,
                    "fields": [
                        "full_name^4",
                        "normalized_name^3",
                        "masked_cpf^3",
                        "legal_name^4",
                        "trade_name^2",
                        "cnpj^4",
                        "contract_number^3",
                        "process_number^2",
                        "object",
                    ],
                    "fuzziness": "AUTO",
                }
            },
        )
    except Exception:
        return []

    items: list[dict[str, Any]] = []
    for hit in response.get("hits", {}).get("hits", []):
        source = hit.get("_source") or {}
        index = str(hit.get("_index") or "")
        entity_type = _entity_type_from_index(index)
        entity_id = str(source.get("id") or hit.get("_id"))
        label = (
            source.get("full_name")
            or source.get("legal_name")
            or source.get("contract_number")
            or entity_id
        )
        items.append(
            {
                "id": entity_id,
                "entity_type": entity_type,
                "label": label,
                "subtitle": source.get("cnpj") or source.get("party_acronym") or index,
                "href": _href_for_entity(entity_type, entity_id),
                "score": hit.get("_score"),
                "source": source,
            }
        )
    return items


def _entity_type_from_index(index: str) -> str:
    if "person" in index:
        return "person"
    if "compan" in index:
        return "company"
    if "contract" in index:
        return "contract"
    return "entity"


def _href_for_entity(entity_type: str, entity_id: str) -> str:
    if entity_type == "person":
        return f"/politicos/{entity_id}"
    if entity_type == "company":
        return f"/empresas/{entity_id}"
    if entity_type == "contract":
        return f"/contratos/{entity_id}"
    return "/"
