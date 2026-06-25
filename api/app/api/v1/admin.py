import json
from datetime import datetime, timezone
from typing import Any

import redis
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.cache import redis_client
from app.core.celery_app import celery_app
from app.db.database import engine
from app.modules.auth.auth_service import get_current_user
from app.modules.workers.ingestion_tasks import run_massive_ingestion


router = APIRouter(prefix="/admin", tags=["admin"])


class MassiveIngestionRequest(BaseModel):
    source_key: str = Field(default="all", min_length=2, max_length=120)


@router.get("/system-health")
def get_system_health(current_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    services = [
        _api_health(),
        _postgres_health(),
        _redis_health(),
        _celery_health(),
    ]
    has_error = any(service["status"] == "error" for service in services)
    has_warning = any(service["status"] == "warning" for service in services)

    if has_error:
        status_value = "error"
    elif has_warning:
        status_value = "degraded"
    else:
        status_value = "success"

    return {
        "status": status_value,
        "requested_by": current_user["email"],
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "services": services,
    }


@router.get("/system-logs")
def get_system_logs(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(default=25, ge=1, le=100),
) -> dict[str, Any]:
    logs = _read_task_logs(limit=limit)

    if not logs:
        logs = [
            {
                "id": "system-no-recent-tasks",
                "status": "success",
                "title": "Sistema sem tarefas recentes",
                "message": "Nenhum erro ou processamento recente foi encontrado.",
                "technical_details": {
                    "source": "redis",
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


@router.post("/ingestion/run", status_code=status.HTTP_202_ACCEPTED)
def trigger_massive_ingestion(
    payload: MassiveIngestionRequest,
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    task = run_massive_ingestion.delay(payload.source_key)
    _record_admin_task_submission(
        task_id=task.id,
        job="massive_ingestion",
        title="Varredura governamental massiva",
        requested_by=current_user["email"],
        metadata={"source_key": payload.source_key},
    )
    return {
        "status": "accepted",
        "job": "massive_ingestion",
        "task_id": task.id,
        "source_key": payload.source_key,
        "requested_by": current_user["email"],
        "message": "Os robos de coleta foram iniciados em segundo plano.",
    }


def _api_health() -> dict[str, Any]:
    return {
        "name": "api",
        "status": "ok",
        "message": "FastAPI online e respondendo.",
        "technical_details": {"component": "fastapi"},
    }


def _postgres_health() -> dict[str, Any]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        return {
            "name": "postgres",
            "status": "error",
            "message": "PostgreSQL indisponivel para consultas.",
            "technical_details": {"exception": repr(exc)},
        }

    return {
        "name": "postgres",
        "status": "ok",
        "message": "Banco PostgreSQL conectado.",
        "technical_details": {"component": "postgres"},
    }


def _redis_health() -> dict[str, Any]:
    try:
        redis_client.ping()
    except redis.RedisError as exc:
        return {
            "name": "redis",
            "status": "error",
            "message": "Redis indisponivel. Fila, cache e logs podem falhar.",
            "technical_details": {"exception": repr(exc)},
        }

    return {
        "name": "redis",
        "status": "ok",
        "message": "Redis conectado para fila, cache e logs.",
        "technical_details": {"component": "redis"},
    }


def _celery_health() -> dict[str, Any]:
    try:
        response = celery_app.control.inspect(timeout=1.0).ping()
    except Exception as exc:
        return {
            "name": "celery",
            "status": "error",
            "message": "Nao foi possivel consultar o worker Celery.",
            "technical_details": {"exception": repr(exc)},
        }

    if not response:
        return {
            "name": "celery",
            "status": "warning",
            "message": "Nenhum worker Celery respondeu ao ping. Tarefas podem ficar aguardando.",
            "technical_details": {"ping": response},
        }

    return {
        "name": "celery",
        "status": "ok",
        "message": f"{len(response)} worker(s) Celery respondendo.",
        "technical_details": {"ping": response},
    }


def _read_task_logs(limit: int) -> list[dict[str, Any]]:
    try:
        celery_keys = list(redis_client.scan_iter("celery-task-meta-*", count=limit * 2))
        admin_keys = list(redis_client.scan_iter("admin-system-log-*", count=limit * 2))
    except redis.RedisError as exc:
        return [
            {
                "id": "redis-log-read-error",
                "status": "error",
                "title": "Redis indisponivel",
                "message": "Nao foi possivel consultar os logs das tarefas agora.",
                "technical_details": {"exception": repr(exc)},
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]

    logs_by_id: dict[str, dict[str, Any]] = {}

    for key in admin_keys[:limit]:
        metadata = _load_json_key(str(key))
        task_id = str(metadata.get("task_id") or str(key).replace("admin-system-log-", "", 1))
        logs_by_id[task_id] = _format_metadata_log(task_id=task_id, metadata=metadata)

    for key in celery_keys[:limit]:
        task_id = str(key).replace("celery-task-meta-", "", 1)
        metadata = _load_json_key(str(key))
        logs_by_id[task_id] = _format_metadata_log(task_id=task_id, metadata=metadata)

    logs = list(logs_by_id.values())
    logs.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return logs[:limit]


def _load_json_key(key: str) -> dict[str, Any]:
    try:
        raw_value = redis_client.get(key)
    except redis.RedisError as exc:
        return {
            "status": "FAILURE",
            "result": {"exception": repr(exc)},
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
            "result": {"raw": raw_value},
            "traceback": None,
            "date_done": datetime.now(timezone.utc).isoformat(),
        }

    return payload if isinstance(payload, dict) else {"status": "UNKNOWN", "result": payload}


def _format_metadata_log(task_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
    raw_status = str(metadata.get("status") or "UNKNOWN").upper()
    if raw_status == "UNKNOWN":
        raw_status = str(AsyncResult(task_id, app=celery_app).status or "UNKNOWN").upper()

    result = metadata.get("result")
    traceback_text = metadata.get("traceback")
    created_at = (
        metadata.get("created_at")
        or metadata.get("date_done")
        or datetime.now(timezone.utc).isoformat()
    )
    status = _normalized_status(raw_status)
    if status == "success" and _result_has_warnings(result):
        status = "warning"

    return {
        "id": task_id,
        "status": status,
        "title": str(metadata.get("title") or _friendly_title(result=result, raw_status=raw_status)),
        "message": _friendly_message(result=result, raw_status=raw_status, status=status),
        "technical_details": {
            "task_id": task_id,
            "celery_status": raw_status,
            "metadata": metadata,
            "result": result,
            "traceback": traceback_text,
        },
        "created_at": str(created_at),
    }


def _normalized_status(raw_status: str) -> str:
    if raw_status in {"FAILURE", "REVOKED"}:
        return "error"
    if raw_status in {"PENDING", "RECEIVED", "STARTED", "RETRY"}:
        return "running"
    return "success"


def _result_has_warnings(result: Any) -> bool:
    return isinstance(result, dict) and bool(result.get("errors"))


def _friendly_title(result: Any, raw_status: str) -> str:
    if isinstance(result, dict):
        job = result.get("job")
        if job == "political_ingestion":
            return "Sincronizacao politica nacional"
        if job == "daily_ingestion":
            return "Ingestao Portal da Transparencia"
        if job == "massive_ingestion":
            return "Varredura governamental massiva"
        if "politicians_found" in result:
            return "Sincronizacao de politicos"
        if "contracts_saved" in result or "expenses_saved" in result:
            return "Ingestao de despesas e contratos"

    if raw_status == "FAILURE":
        return "Tarefa com erro"
    if raw_status in {"PENDING", "RECEIVED", "STARTED", "RETRY"}:
        return "Tarefa em processamento"
    return "Tarefa concluida"


def _friendly_message(result: Any, raw_status: str, status: str) -> str:
    if status == "error":
        return "O processamento falhou. Abra os detalhes tecnicos para ver a causa."
    if status == "running":
        return "A tarefa foi enviada e ainda esta em execucao ou aguardando o worker."

    if isinstance(result, dict):
        if result.get("job") == "massive_ingestion":
            processed = result.get("sources_processed", 0)
            rows = result.get("rows_collected", 0)
            synced = result.get("nodes_synced", 0)
            errors = result.get("errors") or []
            if errors:
                return (
                    f"Varredura processou {processed} fonte(s), coletou {rows} "
                    f"registro(s) e sincronizou {synced} no grafo com {len(errors)} aviso(s)."
                )
            return (
                f"Varredura processou {processed} fonte(s), coletou {rows} "
                f"registro(s) e sincronizou {synced} no grafo."
            )

        errors = result.get("errors") or []
        politicians = result.get("politicians_saved")
        found = result.get("politicians_found")
        expenses = result.get("expenses_saved")
        if politicians is not None:
            counts = result.get("source_counts") or {}
            source_text = ""
            if isinstance(counts, dict) and counts:
                source_text = (
                    f" Fontes: Camara {counts.get('dados-abertos-camara', 0)}, "
                    f"Senado {counts.get('dados-abertos-senado', 0)}, "
                    f"TSE 2024 {counts.get('dados-abertos-tse-2024', 0)}, "
                    f"TSE 2022 {counts.get('dados-abertos-tse-2022', 0)}."
                )
            base = f"{politicians} de {found or politicians} politicos ativos salvos"
            if expenses is not None:
                base = f"{base}; {expenses} despesas processadas"
            if errors:
                return f"{base}.{source_text} A coleta terminou com {len(errors)} aviso(s)."
            return f"{base}.{source_text} Coleta concluida."

        contracts = result.get("contracts_saved")
        if contracts is not None:
            return f"{contracts} contratos e {result.get('expenses_saved', 0)} despesas salvos."

    if raw_status == "SUCCESS":
        return "A tarefa terminou sem erros registrados."
    return f"Status atual: {raw_status}."


def _record_admin_task_submission(
    task_id: str,
    job: str,
    title: str,
    requested_by: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    payload = {
        "task_id": task_id,
        "job": job,
        "title": title,
        "requested_by": requested_by,
        "status": "PENDING",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }
    try:
        redis_client.setex(
            f"admin-system-log-{task_id}",
            86400,
            json.dumps(payload, default=str),
        )
    except redis.RedisError:
        return
