import logging
import re
from hashlib import sha256
from time import time

import redis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.trustedhost import TrustedHostMiddleware

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
from app.core.cache import redis_client
from app.core.config import settings
from app.db import models
from app.db.database import SessionLocal, engine
from app.db.schema_maintenance import ensure_postgres_runtime_schema
from app.modules.auth.auth_service import ensure_system_roles
from app.modules.graphs.sync_service import GraphSyncService


logger = logging.getLogger(__name__)

app = FastAPI(
    title="ONGP - PEGA RATAO API",
    version="0.1.0",
    description="Motor inicial do Observatorio Nacional de Gastos Publicos.",
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.trusted_hosts,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_origin_regex=settings.cors_allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
    ],
    expose_headers=[
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
    ],
    max_age=600,
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
    response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
    if settings.SECURITY_HSTS_ENABLED:
        response.headers.setdefault(
            "Strict-Transport-Security",
            f"max-age={settings.SECURITY_HSTS_MAX_AGE_SECONDS}; includeSubDomains",
        )
    return response


@app.middleware("http")
async def request_abuse_guard_middleware(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            parsed_length = int(content_length)
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length."})
        if parsed_length > settings.MAX_REQUEST_BODY_BYTES:
            return JSONResponse(status_code=413, content={"detail": "Request body too large."})

    if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if origin and not _origin_allowed(origin):
            return JSONResponse(status_code=403, content={"detail": "Origin not allowed."})

    return await call_next(request)


@app.middleware("http")
async def redis_rate_limit_middleware(request: Request, call_next):
    if _is_rate_limit_exempt(request):
        return await call_next(request)

    identity = _rate_limit_identity(request)
    try:
        long_hit = _rate_limit_hit(
            key=f"rl:v1:{identity}:long",
            limit=settings.RATE_LIMIT_MAX_REQUESTS,
            window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
        )
        burst_hit = _rate_limit_hit(
            key=f"rl:v1:{identity}:burst",
            limit=settings.RATE_LIMIT_BURST_MAX_REQUESTS,
            window_seconds=settings.RATE_LIMIT_BURST_WINDOW_SECONDS,
        )
    except redis.RedisError:
        logger.exception("rate_limit_redis_unavailable")
        return JSONResponse(
            status_code=503,
            content={"detail": "Rate limiter unavailable."},
            headers={"Retry-After": "30"},
        )

    active_hit = burst_hit if burst_hit["blocked"] else long_hit
    if long_hit["blocked"] or burst_hit["blocked"]:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests."},
            headers={
                "Retry-After": str(active_hit["reset_seconds"]),
                "X-RateLimit-Limit": str(active_hit["limit"]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(active_hit["reset_epoch"]),
            },
        )

    response = await call_next(request)
    response.headers.setdefault("X-RateLimit-Limit", str(long_hit["limit"]))
    response.headers.setdefault("X-RateLimit-Remaining", str(long_hit["remaining"]))
    response.headers.setdefault("X-RateLimit-Reset", str(long_hit["reset_epoch"]))
    return response


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
    _validate_runtime_security()
    models.Base.metadata.create_all(bind=engine)
    ensure_postgres_runtime_schema(engine)
    with SessionLocal() as db:
        ensure_system_roles(db)
    try:
        GraphSyncService().ensure_constraints()
    except Exception as exc:
        logger.warning("neo4j_startup_constraints_skipped: %s", exc)


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


def _is_rate_limit_exempt(request: Request) -> bool:
    if not settings.RATE_LIMIT_ENABLED:
        return True
    if request.method == "OPTIONS":
        return True
    return request.url.path in {"/", "/health", "/health/db", "/metrics"}


def _rate_limit_identity(request: Request) -> str:
    authorization = request.headers.get("authorization") or ""
    if authorization.lower().startswith("bearer "):
        token_digest = sha256(authorization.encode("utf-8")).hexdigest()[:32]
        return f"token:{token_digest}"

    client_host = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first_hop = forwarded_for.split(",", 1)[0].strip()
        if first_hop:
            client_host = first_hop
    return f"ip:{sha256(client_host.encode('utf-8')).hexdigest()[:32]}"


def _rate_limit_hit(
    key: str,
    limit: int,
    window_seconds: int,
) -> dict[str, int | bool]:
    count = int(redis_client.incr(key))
    if count == 1:
        redis_client.expire(key, window_seconds)
    ttl = int(redis_client.ttl(key))
    if ttl < 0:
        redis_client.expire(key, window_seconds)
        ttl = window_seconds
    reset_epoch = int(time()) + ttl
    remaining = max(0, limit - count)
    return {
        "blocked": count > limit,
        "limit": limit,
        "remaining": remaining,
        "reset_epoch": reset_epoch,
        "reset_seconds": max(1, ttl),
    }


def _validate_runtime_security() -> None:
    if settings.APP_ENV.lower() not in {"prod", "production"}:
        return
    if settings.JWT_SECRET_KEY == "ongp-local-dev-secret-change-me":
        raise RuntimeError("JWT_SECRET_KEY must be changed in production.")
    if not settings.AUTH_COOKIE_SECURE:
        raise RuntimeError("AUTH_COOKIE_SECURE must be true in production.")
    if not settings.cors_allowed_origins and not settings.cors_allowed_origin_regex:
        raise RuntimeError("CORS_ALLOWED_ORIGINS or CORS_ALLOWED_ORIGIN_REGEX must be configured in production.")


def _origin_allowed(origin: str) -> bool:
    if origin in settings.cors_allowed_origins:
        return True
    if settings.cors_allowed_origin_regex:
        return re.fullmatch(settings.cors_allowed_origin_regex, origin) is not None
    return False
