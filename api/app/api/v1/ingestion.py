import json
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.cache import redis_client
from app.db.database import get_db
from app.modules.auth.auth_service import get_current_user
from app.modules.ingestion.political_transparency import PoliticalTransparencyIngestion
from app.workers.ingestion_tasks import (
    task_run_daily_ingestion,
    task_run_political_ingestion,
)


router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
def trigger_daily_ingestion(
    current_user: dict = Depends(get_current_user),
    data_inicio: date | None = None,
    data_fim: date | None = None,
    codigo_orgao: str | None = None,
    pagina: int = 1,
) -> dict[str, Any]:
    task = task_run_daily_ingestion.delay(
        data_inicio=data_inicio.isoformat() if data_inicio else None,
        data_fim=data_fim.isoformat() if data_fim else None,
        codigo_orgao=codigo_orgao,
        pagina=pagina,
    )
    _record_admin_task_submission(
        task_id=task.id,
        job="daily_ingestion",
        title="Ingestao Portal da Transparencia",
        requested_by=current_user["email"],
    )
    return {
        "status": "accepted",
        "job": "daily_ingestion",
        "task_id": task.id,
        "requested_by": current_user["email"],
        "params": {
            "data_inicio": data_inicio.isoformat() if data_inicio else None,
            "data_fim": data_fim.isoformat() if data_fim else None,
            "codigo_orgao": codigo_orgao,
            "pagina": pagina,
        },
    }


@router.post("/politicians/run")
def trigger_political_ingestion(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    pagina: int = Query(default=1, ge=1),
    itens: int = Query(default=100, ge=1, le=100),
    ano: int | None = Query(default=None, ge=2008),
    despesas_por_politico: int = Query(default=100, ge=0, le=500),
    paginas_camara: int = Query(default=1, ge=1, le=20),
    incluir_senado: bool = Query(default=True),
    despesas_senado: bool = Query(default=False),
    sync: bool = Query(default=False),
) -> dict[str, Any]:
    if sync:
        return _run_political_ingestion_now(
            db=db,
            requested_by=current_user["email"],
            pagina=pagina,
            itens=itens,
            ano=ano,
            despesas_por_politico=despesas_por_politico,
            paginas_camara=paginas_camara,
            incluir_senado=incluir_senado,
            despesas_senado=despesas_senado,
        )

    task = task_run_political_ingestion.delay(
        pagina=pagina,
        itens=itens,
        ano=ano,
        despesas_por_politico=despesas_por_politico,
        paginas_camara=paginas_camara,
        incluir_senado=incluir_senado,
        despesas_senado=despesas_senado,
    )
    _record_admin_task_submission(
        task_id=task.id,
        job="political_ingestion",
        title="Sincronizacao Camara/Senado",
        requested_by=current_user["email"],
    )
    return {
        "status": "accepted",
        "job": "political_ingestion",
        "task_id": task.id,
        "requested_by": current_user["email"],
        "params": {
            "pagina": pagina,
            "itens": itens,
            "ano": ano,
            "despesas_por_politico": despesas_por_politico,
            "paginas_camara": paginas_camara,
            "incluir_senado": incluir_senado,
            "despesas_senado": despesas_senado,
            "sync": sync,
        },
    }


def _run_political_ingestion_now(
    db: Session,
    requested_by: str,
    pagina: int,
    itens: int,
    ano: int | None,
    despesas_por_politico: int,
    paginas_camara: int,
    incluir_senado: bool,
    despesas_senado: bool,
) -> dict[str, Any]:
    task_id = f"sync-political-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    _record_admin_task_submission(
        task_id=task_id,
        job="political_ingestion",
        title="Sincronizacao Camara/Senado",
        requested_by=requested_by,
    )

    try:
        service = PoliticalTransparencyIngestion(db=db)
        result = service.run(
            pagina=pagina,
            itens=itens,
            ano=ano,
            despesas_por_politico=despesas_por_politico,
            paginas_camara=paginas_camara,
            incluir_senado=incluir_senado,
            despesas_senado=despesas_senado,
            sync_graph=False,
        )
    except Exception as exc:
        error_payload = {"exception": repr(exc)}
        _record_admin_task_result(
            task_id=task_id,
            job="political_ingestion",
            title="Sincronizacao Camara/Senado",
            requested_by=requested_by,
            status_value="FAILURE",
            result=error_payload,
        )
        raise

    payload = {
        "status": "completed",
        "job": "political_ingestion",
        "task_id": task_id,
        "requested_by": requested_by,
        **result.to_dict(),
    }
    _record_admin_task_result(
        task_id=task_id,
        job="political_ingestion",
        title="Sincronizacao Camara/Senado",
        requested_by=requested_by,
        status_value="SUCCESS",
        result=payload,
    )
    return payload


def _record_admin_task_submission(
    task_id: str,
    job: str,
    title: str,
    requested_by: str,
) -> None:
    payload = {
        "task_id": task_id,
        "job": job,
        "title": title,
        "requested_by": requested_by,
        "status": "PENDING",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_admin_task_log(task_id=task_id, payload=payload)


def _record_admin_task_result(
    task_id: str,
    job: str,
    title: str,
    requested_by: str,
    status_value: str,
    result: dict[str, Any],
) -> None:
    payload = {
        "task_id": task_id,
        "job": job,
        "title": title,
        "requested_by": requested_by,
        "status": status_value,
        "result": result,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_admin_task_log(task_id=task_id, payload=payload)


def _write_admin_task_log(task_id: str, payload: dict[str, Any]) -> None:
    try:
        redis_client.setex(
            f"admin-system-log-{task_id}",
            86400,
            json.dumps(payload, default=str),
        )
    except Exception:
        return
