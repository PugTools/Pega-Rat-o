from fastapi import APIRouter, Depends, Query
from sqlalchemy import case
from sqlalchemy.orm import Session

from app.core.cache import get_json_cache, set_json_cache
from app.db.database import get_db
from app.db.models import RiskAlert
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
