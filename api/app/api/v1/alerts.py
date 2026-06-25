from datetime import datetime, timezone
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case
from sqlalchemy.orm import Session

from app.core.cache import get_json_cache, set_json_cache
from app.db.database import get_db
from app.db.models import RiskAlert
from app.modules.alerts.graph_risk_queries import run_graph_audit_suite
from app.schemas.core_schemas import RiskAlertResponse


router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[RiskAlertResponse])
def list_alerts(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    status: str | None = None,
) -> list[RiskAlert]:
    cache_key = f"alerts:list:{limit}:{status or 'all'}"
    cached = get_json_cache(cache_key)
    if cached is not None:
        return cached

    severity_rank = case(
        (RiskAlert.severity == "critical", 1),
        (RiskAlert.severity == "high", 2),
        (RiskAlert.severity == "medium", 3),
        (RiskAlert.severity == "low", 4),
        else_=5,
    )
    query = db.query(RiskAlert)
    if status:
        query = query.filter(RiskAlert.status == status)

    alerts = query.order_by(severity_rank, RiskAlert.created_at.desc()).limit(limit).all()
    payload = [RiskAlertResponse.model_validate(alert).model_dump(mode="json") for alert in alerts]
    set_json_cache(cache_key, payload, ttl_seconds=600)
    return payload


@router.get("/entity/{entity_type}/{entity_id}")
def list_entity_alerts(
    entity_type: str,
    entity_id: UUID,
    db: Session = Depends(get_db),
    include_graph: bool = Query(default=True),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict[str, Any]]:
    normalized_type = _normalize_entity_type(entity_type)
    cache_key = f"alerts:entity:{normalized_type}:{entity_id}:{include_graph}:{limit}"
    cached = get_json_cache(cache_key)
    if cached is not None:
        return cached

    alerts = _persisted_entity_alerts(
        db=db,
        entity_type=normalized_type,
        entity_id=entity_id,
        limit=limit,
    )

    if include_graph:
        alerts.extend(
            _graph_entity_alerts(
                entity_type=normalized_type,
                entity_id=str(entity_id),
                limit=limit,
            )
        )

    alerts.sort(key=_alert_sort_key)
    payload = alerts[:limit]
    set_json_cache(cache_key, payload, ttl_seconds=300)
    return payload


def _persisted_entity_alerts(
    db: Session,
    entity_type: str,
    entity_id: UUID,
    limit: int,
) -> list[dict[str, Any]]:
    severity_rank = case(
        (RiskAlert.severity == "critical", 1),
        (RiskAlert.severity == "high", 2),
        (RiskAlert.severity == "medium", 3),
        (RiskAlert.severity == "low", 4),
        else_=5,
    )
    rows = (
        db.query(RiskAlert)
        .filter(RiskAlert.entity_type == entity_type)
        .filter(RiskAlert.entity_id == entity_id)
        .order_by(severity_rank, RiskAlert.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        RiskAlertResponse.model_validate(alert).model_dump(mode="json")
        for alert in rows
    ]


def _graph_entity_alerts(
    entity_type: str,
    entity_id: str,
    limit: int,
) -> list[dict[str, Any]]:
    try:
        graph_alerts = run_graph_audit_suite()
    except Exception:
        return []

    filtered: list[dict[str, Any]] = []
    for alert in graph_alerts:
        evidence = alert.get("evidence") or {}
        if not _graph_alert_matches_entity(entity_type, entity_id, alert, evidence):
            continue

        alert_id = uuid5(
            NAMESPACE_URL,
            f"graph-alert:{entity_type}:{entity_id}:{alert.get('alert_type')}:{evidence}",
        )
        filtered.append(
            {
                "id": str(alert_id),
                "entity_type": alert.get("entity_type") or entity_type,
                "entity_id": alert.get("entity_id") or entity_id,
                "alert_type": alert.get("alert_type") or "graph_risk",
                "severity": alert.get("severity") or "high",
                "score": alert.get("score") or "80.000",
                "title": alert.get("title") or "Sinal de risco no grafo",
                "explanation": alert.get("explanation") or "",
                "evidence": evidence,
                "status": alert.get("status") or "open",
                "created_at": alert.get("created_at")
                or datetime.now(timezone.utc).isoformat(),
                "source": "neo4j_cypher",
            }
        )
        if len(filtered) >= limit:
            break
    return filtered


def _graph_alert_matches_entity(
    entity_type: str,
    entity_id: str,
    alert: dict[str, Any],
    evidence: dict[str, Any],
) -> bool:
    candidate_keys = {
        "entity_id",
        f"{entity_type}_id",
        "politician_id" if entity_type == "person" else "",
        "company_id" if entity_type == "company" else "",
        "contract_id" if entity_type == "contract" else "",
        "organization_id" if entity_type == "organization" else "",
    }
    values = {str(alert.get("entity_id") or "")}
    values.update(str(evidence.get(key) or "") for key in candidate_keys if key)
    return entity_id in values


def _normalize_entity_type(entity_type: str) -> str:
    aliases = {
        "politico": "person",
        "politicos": "person",
        "person": "person",
        "persons": "person",
        "empresa": "company",
        "empresas": "company",
        "company": "company",
        "companies": "company",
        "contrato": "contract",
        "contract": "contract",
        "orgao": "organization",
        "organization": "organization",
    }
    return aliases.get(entity_type.lower(), entity_type.lower())


def _alert_sort_key(alert: dict[str, Any]) -> tuple[int, float]:
    severity_rank = {
        "critical": 1,
        "high": 2,
        "medium": 3,
        "low": 4,
    }.get(str(alert.get("severity", "")).lower(), 5)
    return severity_rank, _created_at_desc_value(alert.get("created_at"))


def _created_at_desc_value(value: Any) -> float:
    if not value:
        return 0.0
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    return -parsed.timestamp()
