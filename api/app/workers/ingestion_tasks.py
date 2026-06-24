from datetime import date
from typing import Any

from app.core.celery_app import celery_app
from app.db.database import SessionLocal
from app.modules.ingestion.camara_senado_client import CamaraDadosAbertosClient
from app.modules.ingestion.pipeline import IngestionPipeline
from app.modules.ingestion.political_transparency import PoliticalTransparencyIngestion


@celery_app.task(name="app.workers.ingestion_tasks.task_run_daily_ingestion")
def task_run_daily_ingestion(
    data_inicio: str | None = None,
    data_fim: str | None = None,
    codigo_orgao: str | None = None,
    pagina: int = 1,
) -> dict[str, Any]:
    db = SessionLocal()
    try:
        pipeline = IngestionPipeline(db=db)
        result = pipeline.run_daily_ingestion(
            data_inicio=_parse_date(data_inicio),
            data_fim=_parse_date(data_fim),
            codigo_orgao=codigo_orgao,
            pagina=pagina,
        )
        return {"job": "daily_ingestion", **result.to_dict()}
    finally:
        db.close()


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


@celery_app.task(name="app.workers.ingestion_tasks.task_fetch_camara_deputado_expenses")
def task_fetch_camara_deputado_expenses(
    deputado_id: str,
    ano: int,
    mes: int | None = None,
) -> dict[str, Any]:
    client = CamaraDadosAbertosClient()
    expenses = client.fetch_deputado_despesas(deputado_id=deputado_id, ano=ano, mes=mes)
    return {"deputado_id": deputado_id, "count": len(expenses)}


@celery_app.task(name="app.workers.ingestion_tasks.task_run_political_ingestion")
def task_run_political_ingestion(
    pagina: int = 1,
    itens: int = 25,
    ano: int | None = None,
    despesas_por_politico: int = 100,
    paginas_camara: int = 1,
    incluir_senado: bool = True,
    despesas_senado: bool = False,
    incluir_tse: bool = False,
    anos_tse: list[int] | None = None,
    limite_tse_por_cargo: int = 50,
    uf_tse: str | None = None,
    patrimonio_tse: bool = True,
) -> dict[str, Any]:
    db = SessionLocal()
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
            incluir_tse=incluir_tse,
            anos_tse=anos_tse,
            limite_tse_por_cargo=limite_tse_por_cargo,
            uf_tse=uf_tse,
            patrimonio_tse=patrimonio_tse,
        )
        return {"job": "political_ingestion", **result.to_dict()}
    finally:
        db.close()
