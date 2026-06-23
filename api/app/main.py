from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.alerts import router as alerts_router
from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.backoffice import router as backoffice_router
from app.api.v1.companies import router as companies_router
from app.api.v1.copilot import router as copilot_router
from app.api.v1.contracts import router as contracts_router
from app.api.v1.expenses import router as expenses_router
from app.api.v1.graphs import router as graphs_router
from app.api.v1.ingestion import router as ingestion_router
from app.api.v1.persons import router as persons_router
from app.api.v1.reports import router as reports_router
from app.api.v1.search import router as search_router
from app.db import models
from app.db.database import engine
from app.db.schema_maintenance import ensure_postgres_runtime_schema
from app.modules.graphs.sync_service import GraphSyncService

app = FastAPI(
    title="ONGP - PEGA RATAO API",
    version="0.1.0",
    description="Motor inicial do Observatorio Nacional de Gastos Publicos.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(companies_router, prefix="/api/v1")
app.include_router(persons_router, prefix="/api/v1")
app.include_router(contracts_router, prefix="/api/v1")
app.include_router(expenses_router, prefix="/api/v1")
app.include_router(ingestion_router, prefix="/api/v1")
app.include_router(graphs_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(copilot_router, prefix="/api/v1")
app.include_router(backoffice_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")

Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.on_event("startup")
def on_startup() -> None:
    models.Base.metadata.create_all(bind=engine)
    ensure_postgres_runtime_schema(engine)
    try:
        GraphSyncService().ensure_constraints()
    except RuntimeError:
        pass


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "Observatorio Nacional de Gastos Publicos",
        "codename": "PEGA RATAO",
        "status": "online",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def database_health() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        return {"status": "error", "detail": str(exc)}

    return {"status": "ok"}
