from datetime import date
from datetime import datetime, timezone
import json
from typing import Any

from fastapi import APIRouter, Depends, Query, status

from app.core.cache import redis_client
from app.modules.auth.auth_service import get_current_user
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
        title="Ingestão Portal da Transparência",
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
    pagina: int = Query(default=1, ge=1),
    itens: int = Query(default=100, ge=1, le=100),
    ano: int | None = Query(default=None, ge=2008),
    despesas_por_politico: int = Query(default=100, ge=0, le=500),
    paginas_camara: int = Query(default=1, ge=1, le=20),
    incluir_senado: bool = Query(default=True),
    despesas_senado: bool = Query(default=False),
) -> dict[str, Any]:
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
        title="Sincronização Câmara/Senado",
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
        },
    }


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
    try:
        redis_client.setex(
            f"admin-system-log-{task_id}",
            86400,
            json.dumps(payload, default=str),
        )
    except Exception:
        return
