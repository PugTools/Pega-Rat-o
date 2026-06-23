import functools
import hashlib
import inspect
import json
from typing import Any, Callable

from fastapi import Request
from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import AuditLog


def log_audit(action: str, resource_type: str | None = None) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = func(*args, **kwargs)
            _write_audit_log(action, resource_type, args, kwargs)
            return result

        wrapper.__signature__ = inspect.signature(func)  # type: ignore[attr-defined]
        return wrapper

    return decorator


def _write_audit_log(
    action: str,
    resource_type: str | None,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> None:
    request = _find_request(args, kwargs)
    current_user = kwargs.get("current_user") or {}
    db = SessionLocal()
    try:
        previous = db.scalar(select(AuditLog).order_by(AuditLog.created_at.desc()))
        previous_hash = previous.current_hash if previous else None
        metadata = {
            "path": str(request.url.path) if request else None,
            "method": request.method if request else None,
            "query": dict(request.query_params) if request else {},
            "user": current_user.get("email"),
        }
        current_hash = _hash_payload(action, resource_type, metadata, previous_hash)
        db.add(
            AuditLog(
                action=action,
                resource_type=resource_type,
                resource_id=None,
                ip_address=request.client.host if request and request.client else None,
                user_agent=request.headers.get("user-agent") if request else None,
                metadata_json=metadata,
                previous_hash=previous_hash,
                current_hash=current_hash,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _find_request(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Request | None:
    for value in list(args) + list(kwargs.values()):
        if isinstance(value, Request):
            return value
    return None


def _hash_payload(
    action: str,
    resource_type: str | None,
    metadata: dict[str, Any],
    previous_hash: str | None,
) -> str:
    payload = {
        "action": action,
        "resource_type": resource_type,
        "metadata": metadata,
        "previous_hash": previous_hash,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
