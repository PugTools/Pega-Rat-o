from decimal import Decimal
from typing import Any


DEFAULT_RISK_SETTINGS: dict[str, Any] = {
    "expense_fragmentation_legal_limit": "50000.00",
    "expense_fragmentation_minimum_count": 3,
    "expense_fragmentation_window_days": 30,
    "supplier_concentration_threshold": "0.70",
    "supplier_concentration_minimum_total_amount": "100000.00",
    "abnormal_growth_threshold": "3.00",
    "abnormal_growth_minimum_history": 3,
}

runtime_risk_settings: dict[str, Any] = DEFAULT_RISK_SETTINGS.copy()


def get_risk_settings() -> dict[str, Any]:
    return runtime_risk_settings.copy()


def update_risk_settings(payload: dict[str, Any]) -> dict[str, Any]:
    for key, value in payload.items():
        if key in runtime_risk_settings and value is not None:
            runtime_risk_settings[key] = str(value) if isinstance(value, Decimal) else value
    return get_risk_settings()
