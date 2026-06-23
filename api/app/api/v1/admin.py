import json
from datetime import datetime, timezone
from typing import Any

import redis
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, Query

from app.core.cache import redis_client
from app.core.celery_app import celery_app
from app.modules.auth.auth_service import get_current_user


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/system-logs")
def get_system_logs(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(default=25, ge=1, le=100),
) -> dict[str, Any]:
    logs = _read_celery_task_logs(limit=limit)

    if not logs:
        logs = [
            {
                "id": "system-no-recent-tasks",
                "status": "success",
                "title": "Sistema sem tarefas recentes",
                "message": "Nenhum erro ou processamento recente foi encontrado no Redis.",
                "technical_details": {
                    "source": "redis",
                    "key_pattern": "celery-task-meta-*",
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]

    return {
        "status": "success",
        "requested_by": current_user["email"],
        "logs": logs,
    }


def _read_celery_task_logs(limit: int) -> list[dict[str, Any]]:
    try:
        keys = list(redis_client.scan_iter("celery-task-meta-*", count=limit * 2))
        submitted_keys = list(
            redis_client.scan_iter("admin-system-log-*", count=limit * 2)
        )
    except redis.RedisError as exc:
        return [
            {
                "id": "redis-log-read-error",
                "status": "error",
                "title": "Redis indisponível",
                "message": "Não foi possível consultar os logs das tarefas agora.",
                "technical_details": {"exception": repr(exc)},
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]

    task_logs_by_id: dict[str, dict[str, Any]] = {}
    for key in submitted_keys[:limit]:
        submitted = _load_task_metadata(str(key))
        task_id = str(submitted.get("task_id") or str(key).replace("admin-system-log-", "", 1))
        task_logs_by_id[task_id] = _format_submitted_log(task_id=task_id, metadata=submitted)

    for key in keys[:limit]:
        task_id = str(key).replace("celery-task-meta-", "", 1)
        metadata = _load_task_metadata(str(key))
        task_logs_by_id[task_id] = _format_task_log(task_id=task_id, metadata=metadata)

    task_logs = list(task_logs_by_id.values())
    task_logs.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return task_logs[:limit]


def _load_task_metadata(key: str) -> dict[str, Any]:
    try:
        raw_value = redis_client.get(key)
    except redis.RedisError as exc:
        return {
            "status": "FAILURE",
            "result": repr(exc),
            "traceback": None,
            "date_done": datetime.now(timezone.utc).isoformat(),
        }

    if not raw_value:
        return {"status": "PENDING", "result": None, "traceback": None}

    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError:
        return {
            "status": "FAILURE",
            "result": raw_value,
            "traceback": None,
            "date_done": datetime.now(timezone.utc).isoformat(),
        }

    return payload if isinstance(payload, dict) else {"status": "UNKNOWN", "result": payload}


def _format_task_log(task_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
    task_result = AsyncResult(task_id, app=celery_app)
    raw_status = str(metadata.get("status") or task_result.status or "UNKNOWN").upper()
    result = metadata.get("result")
    traceback_text = metadata.get("traceback")
    created_at = metadata.get("date_done") or datetime.now(timezone.utc).isoformat()

    is_error = raw_status in {"FAILURE", "REVOKED"}
    is_running = raw_status in {"PENDING", "RECEIVED", "STARTED", "RETRY"}

    return {
        "id": task_id,
        "status": "error" if is_error else "running" if is_running else "success",
        "title": _friendly_title(result=result, raw_status=raw_status),
        "message": _friendly_message(
            result=result,
            raw_status=raw_status,
            is_error=is_error,
            is_running=is_running,
        ),
        "technical_details": {
            "task_id": task_id,
            "celery_status": raw_status,
            "result": result,
            "traceback": traceback_text,
        },
        "created_at": created_at,
    }


def _format_submitted_log(task_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": task_id,
        "status": "running",
        "title": str(metadata.get("title") or _friendly_title(metadata, "PENDING")),
        "message": "Tarefa enviada ao Celery e aguardando confirmação do worker.",
        "technical_details": {
            "task_id": task_id,
            "celery_status": metadata.get("status", "PENDING"),
            "submission": metadata,
        },
        "created_at": str(
            metadata.get("created_at") or datetime.now(timezone.utc).isoformat()
        ),
    }


def _friendly_title(result: Any, raw_status: str) -> str:
    if isinstance(result, dict):
        job = result.get("job")
        if job == "political_ingestion":
            return "Sincronização Câmara/Senado"
        if job == "daily_ingestion":
            return "Ingestão Portal da Transparência"
        if "politicians_found" in result:
            return "Sincronização de políticos"
        if "contracts_saved" in result or "expenses_saved" in result:
            return "Ingestão de despesas e contratos"

    if raw_status == "FAILURE":
        return "Tarefa com erro"
    if raw_status in {"PENDING", "RECEIVED", "STARTED", "RETRY"}:
        return "Tarefa em processamento"
    return "Tarefa concluída"


def _friendly_message(
    result: Any,
    raw_status: str,
    is_error: bool,
    is_running: bool,
) -> str:
    if is_error:
        return "O processamento falhou. Abra os detalhes técnicos para ver a causa."
    if is_running:
        return "A tarefa foi enviada e ainda está em execução ou aguardando o worker."

    if isinstance(result, dict):
        errors = result.get("errors")
        if errors:
            return "A tarefa terminou, mas encontrou avisos durante parte da coleta."
        politicians = result.get("politicians_saved")
        expenses = result.get("expenses_saved")
        if politicians is not None:
            return f"{politicians} políticos salvos e {expenses or 0} despesas processadas."
        contracts = result.get("contracts_saved")
        if contracts is not None:
            return f"{contracts} contratos e {result.get('expenses_saved', 0)} despesas salvos."

    if raw_status == "SUCCESS":
        return "A tarefa terminou sem erros registrados."
    return f"Status atual: {raw_status}."
