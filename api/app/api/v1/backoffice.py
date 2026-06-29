from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.modules.auth.auth_service import get_current_user, require_any_role
from app.modules.settings.risk_settings import get_risk_settings, update_risk_settings


router = APIRouter(prefix="/backoffice", tags=["backoffice"])
BACKOFFICE_READ_ROLES = {"system_admin", "source_admin", "auditor", "compliance_officer"}
BACKOFFICE_WRITE_ROLES = {"system_admin", "source_admin"}


class RiskSettingsUpdate(BaseModel):
    expense_fragmentation_legal_limit: str | None = None
    expense_fragmentation_minimum_count: int | None = Field(default=None, ge=1)
    expense_fragmentation_window_days: int | None = Field(default=None, ge=1)
    supplier_concentration_threshold: str | None = None
    supplier_concentration_minimum_total_amount: str | None = None
    abnormal_growth_threshold: str | None = None
    abnormal_growth_minimum_history: int | None = Field(default=None, ge=1)


@router.get("/risk-settings")
def read_risk_settings(
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_any_role(current_user, BACKOFFICE_READ_ROLES)
    return get_risk_settings()


@router.put("/risk-settings")
def write_risk_settings(
    payload: RiskSettingsUpdate,
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    require_any_role(current_user, BACKOFFICE_WRITE_ROLES)
    return update_risk_settings(payload.model_dump(exclude_unset=True))
