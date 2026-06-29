import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import redis
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.core.cache import redis_client
from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.database import get_db
from app.db.database import engine
from app.db.models import AdminSuggestion, Role, User
from app.modules.ingestion.base_government_connector import REGISTRY_PATH, SourceConfig, load_sources_registry
from app.modules.auth.auth_service import get_current_user, hash_password, require_any_role
from app.modules.workers.ingestion_tasks import SOURCE_ALIASES, run_massive_ingestion


router = APIRouter(prefix="/admin", tags=["admin"])
INGESTION_ADMIN_ROLES = {"system_admin", "source_admin"}
SYSTEM_ADMIN_ROLES = {"system_admin"}
BLOCKED_IPS_KEY = "security:blocked_ips"


class MassiveIngestionRequest(BaseModel):
    source_key: str = Field(default="all", min_length=2, max_length=120)


class SourceActivationRequest(BaseModel):
    enabled: bool


class AdminUserUpdate(BaseModel):
    active: bool | None = None
    roles: list[str] | None = None


class PasswordResetRequest(BaseModel):
    new_password: str | None = Field(default=None, min_length=10, max_length=128)


class AdminSuggestionCreate(BaseModel):
    title: str = Field(min_length=4, max_length=160)
    description: str = Field(min_length=8, max_length=4000)
    category: str = Field(default="operacional", min_length=2, max_length=80)
    priority: str = Field(default="medium", pattern="^(low|medium|high|critical)$")


class AdminSuggestionUpdate(BaseModel):
    status: str | None = Field(default=None, pattern="^(open|reviewing|planned|done|rejected)$")
    priority: str | None = Field(default=None, pattern="^(low|medium|high|critical)$")
    assigned_to_email: EmailStr | None = None


class BlockIpRequest(BaseModel):
    ip_address: str = Field(min_length=3, max_length=64)
    reason: str = Field(default="Bloqueio manual pelo administrador.", max_length=500)


def _require_ingestion_admin(
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    return require_any_role(current_user, INGESTION_ADMIN_ROLES)


def _require_system_admin(
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    return require_any_role(current_user, SYSTEM_ADMIN_ROLES)


@router.get("/overview")
def get_admin_overview(
    db: Session = Depends(get_db),
    current_user: dict = Depends(_require_ingestion_admin),
) -> dict[str, Any]:
    registry = load_sources_registry()
    logs = _read_task_logs(limit=10)
    blocked_ips = _read_blocked_ips()
    return {
        "status": "success",
        "requested_by": current_user["email"],
        "cards": {
            "users": db.query(User).count(),
            "active_users": db.query(User).filter(User.active.is_(True)).count(),
            "open_suggestions": db.query(AdminSuggestion).filter(AdminSuggestion.status == "open").count(),
            "blocked_ips": len(blocked_ips),
            "sources_total": len(registry),
            "sources_enabled": sum(1 for source in registry.values() if source.enabled),
            "recent_errors": len([log for log in logs if log.get("status") in {"error", "warning"}]),
        },
        "blocked_ips": blocked_ips[:5],
        "recent_logs": logs,
    }


@router.get("/users")
def list_admin_users(
    db: Session = Depends(get_db),
    current_user: dict = Depends(_require_system_admin),
) -> dict[str, Any]:
    users = (
        db.query(User)
        .options(selectinload(User.roles))
        .order_by(User.created_at.desc())
        .limit(500)
        .all()
    )
    return {
        "status": "success",
        "requested_by": current_user["email"],
        "items": [_user_payload(user) for user in users],
    }


@router.patch("/users/{user_id}")
def update_admin_user(
    user_id: UUID,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(_require_system_admin),
) -> dict[str, Any]:
    user = _get_user_or_404(db, user_id)
    if payload.active is False and str(user.id) == str(current_user.get("id")):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O administrador nao pode desativar a propria conta.",
        )
    if payload.active is not None:
        user.active = payload.active
    if payload.roles is not None:
        normalized_roles = sorted({role.strip() for role in payload.roles if role.strip()})
        if not normalized_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuario precisa manter ao menos uma role.",
            )
        if str(user.id) == str(current_user.get("id")) and "system_admin" not in normalized_roles:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="O administrador nao pode remover system_admin da propria conta.",
            )
        user.roles = [_get_or_create_role(db, role_name) for role_name in normalized_roles]
    db.commit()
    db.refresh(user)
    _record_admin_task_submission(
        task_id=f"user-update-{user.id}-{int(datetime.now(timezone.utc).timestamp())}",
        job="user_management",
        title="Usuario administrativo atualizado",
        requested_by=current_user["email"],
        metadata={"user_id": str(user.id), "email": user.email},
    )
    return {"status": "success", "user": _user_payload(user)}


@router.post("/users/{user_id}/reset-password")
def reset_admin_user_password(
    user_id: UUID,
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(_require_system_admin),
) -> dict[str, Any]:
    user = _get_user_or_404(db, user_id)
    temporary_password = payload.new_password or _temporary_password()
    user.password_hash = hash_password(temporary_password)
    db.commit()
    _record_admin_task_submission(
        task_id=f"password-reset-{user.id}-{int(datetime.now(timezone.utc).timestamp())}",
        job="user_management",
        title="Senha de usuario redefinida",
        requested_by=current_user["email"],
        metadata={"user_id": str(user.id), "email": user.email},
    )
    return {
        "status": "success",
        "message": "Senha redefinida. Entregue a senha temporaria por canal seguro.",
        "user_id": str(user.id),
        "email": user.email,
        "temporary_password": temporary_password if payload.new_password is None else None,
    }


@router.get("/suggestions")
def list_admin_suggestions(
    db: Session = Depends(get_db),
    current_user: dict = Depends(_require_ingestion_admin),
    status_filter: str | None = Query(default=None, alias="status"),
) -> dict[str, Any]:
    query = db.query(AdminSuggestion)
    if status_filter:
        query = query.filter(AdminSuggestion.status == status_filter)
    suggestions = query.order_by(AdminSuggestion.created_at.desc()).limit(200).all()
    return {
        "status": "success",
        "requested_by": current_user["email"],
        "items": [_suggestion_payload(item) for item in suggestions],
    }


@router.post("/suggestions", status_code=status.HTTP_201_CREATED)
def create_admin_suggestion(
    payload: AdminSuggestionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(_require_ingestion_admin),
) -> dict[str, Any]:
    suggestion = AdminSuggestion(
        title=payload.title.strip(),
        description=payload.description.strip(),
        category=payload.category.strip().lower(),
        priority=payload.priority,
        status="open",
        created_by_email=current_user["email"],
        metadata_json={"source": "admin_panel"},
    )
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)
    return {"status": "success", "suggestion": _suggestion_payload(suggestion)}


@router.patch("/suggestions/{suggestion_id}")
def update_admin_suggestion(
    suggestion_id: UUID,
    payload: AdminSuggestionUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(_require_ingestion_admin),
) -> dict[str, Any]:
    suggestion = db.get(AdminSuggestion, suggestion_id)
    if suggestion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sugestao nao encontrada.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(suggestion, field, str(value) if value is not None else None)
    db.commit()
    db.refresh(suggestion)
    return {"status": "success", "suggestion": _suggestion_payload(suggestion)}


@router.get("/security/blocked-ips")
def list_blocked_ips(
    current_user: dict = Depends(_require_system_admin),
) -> dict[str, Any]:
    return {
        "status": "success",
        "requested_by": current_user["email"],
        "items": _read_blocked_ips(),
    }


@router.post("/security/blocked-ips", status_code=status.HTTP_201_CREATED)
def block_ip_address(
    payload: BlockIpRequest,
    request: Request,
    current_user: dict = Depends(_require_system_admin),
) -> dict[str, Any]:
    ip_address = payload.ip_address.strip()
    if not ip_address or any(char.isspace() for char in ip_address):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="IP invalido.")
    if ip_address == _request_client_ip(request):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O administrador nao pode bloquear o proprio IP da sessao atual.",
        )
    entry = {
        "ip_address": ip_address,
        "reason": payload.reason,
        "blocked_by": current_user["email"],
        "blocked_at": datetime.now(timezone.utc).isoformat(),
    }
    redis_client.hset(BLOCKED_IPS_KEY, ip_address, json.dumps(entry, default=str))
    _record_admin_task_submission(
        task_id=f"ip-block-{ip_address}-{int(datetime.now(timezone.utc).timestamp())}",
        job="security",
        title="IP bloqueado manualmente",
        requested_by=current_user["email"],
        metadata={"ip_address": ip_address, "reason": payload.reason},
    )
    return {"status": "success", "entry": entry}


@router.delete("/security/blocked-ips")
def unblock_ip_address(
    ip_address: str = Query(min_length=3, max_length=64),
    current_user: dict = Depends(_require_system_admin),
) -> dict[str, Any]:
    removed = redis_client.hdel(BLOCKED_IPS_KEY, ip_address.strip())
    _record_admin_task_submission(
        task_id=f"ip-unblock-{ip_address}-{int(datetime.now(timezone.utc).timestamp())}",
        job="security",
        title="IP desbloqueado manualmente",
        requested_by=current_user["email"],
        metadata={"ip_address": ip_address, "removed": bool(removed)},
    )
    return {"status": "success", "removed": bool(removed), "ip_address": ip_address}


@router.get("/ingestion/sources")
def list_massive_ingestion_sources(
    current_user: dict = Depends(_require_ingestion_admin),
) -> dict[str, Any]:
    registry = load_sources_registry()
    raw_registry = _load_raw_sources_registry()
    raw_by_key = {
        str(source.get("key")): source
        for source in raw_registry.get("sources", [])
        if source.get("key")
    }
    items = [
        {
            "key": "all",
            "name": "Todas as fontes habilitadas",
            "enabled": True,
            "source_type": "batch",
            "destination_model": "mixed",
            "base_url": "sources_registry.json",
            "category": "operacional",
            "auth_env": None,
            "auth_header": None,
            "requires_token": False,
            "has_auth_token": True,
            "can_enable": False,
            "activation_notes": [
                "Executa todas as fontes marcadas como enabled=true no registry."
            ],
            "endpoints": {},
        }
    ]
    items.extend(
        _source_payload(key=key, config=config, raw_source=raw_by_key.get(key, {}))
        for key, config in sorted(
            registry.items(),
            key=lambda item: (not item[1].enabled, item[0]),
        )
    )
    return {
        "status": "success",
        "requested_by": current_user["email"],
        "total": len(registry),
        "enabled": sum(1 for source in registry.values() if source.enabled),
        "items": items,
        "activation_help": _activation_help(),
    }


@router.patch("/ingestion/sources/{source_key}")
def update_ingestion_source_activation(
    source_key: str,
    payload: SourceActivationRequest,
    current_user: dict = Depends(_require_ingestion_admin),
) -> dict[str, Any]:
    normalized_key = source_key.strip().lower()
    if normalized_key == "all":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A opcao 'all' e operacional e nao pode ser ativada/desativada.",
        )

    raw_registry = _load_raw_sources_registry()
    raw_sources = raw_registry.get("sources", [])
    source_index = next(
        (
            index
            for index, source in enumerate(raw_sources)
            if str(source.get("key", "")).lower() == normalized_key
        ),
        None,
    )
    if source_index is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fonte nao registrada: {source_key}",
        )

    registry = load_sources_registry()
    config = registry.get(normalized_key)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fonte nao carregada pelo registry: {source_key}",
        )

    readiness = _source_readiness(raw_sources[source_index], config)
    if payload.enabled and not readiness["can_enable"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Fonte ainda nao esta pronta para ativacao segura.",
                "notes": readiness["activation_notes"],
                "required_env": readiness["auth_env"],
                "registry_path": _display_registry_path(),
            },
        )

    raw_sources[source_index]["enabled"] = payload.enabled
    raw_registry["sources"] = raw_sources
    _write_raw_sources_registry(raw_registry)

    updated_registry = load_sources_registry()
    updated_config = updated_registry[normalized_key]
    updated_raw = raw_sources[source_index]
    _record_admin_task_submission(
        task_id=f"source-toggle-{normalized_key}-{int(datetime.now(timezone.utc).timestamp())}",
        job="source_activation",
        title="Configuracao de fonte alterada",
        requested_by=current_user["email"],
        metadata={"source_key": normalized_key, "enabled": payload.enabled},
    )
    return {
        "status": "success",
        "requested_by": current_user["email"],
        "message": (
            "Fonte ativada. Ela entrara na opcao 'all' e no dropdown de execucao."
            if payload.enabled
            else "Fonte desativada. Ela nao sera executada na varredura 'all'."
        ),
        "source": _source_payload(
            key=normalized_key,
            config=updated_config,
            raw_source=updated_raw,
        ),
        "activation_help": _activation_help(),
    }


@router.get("/system-health")
def get_system_health(
    current_user: dict = Depends(_require_ingestion_admin),
) -> dict[str, Any]:
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
    current_user: dict = Depends(_require_ingestion_admin),
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
    current_user: dict = Depends(_require_ingestion_admin),
) -> dict[str, Any]:
    requested_source_key = payload.source_key.strip().lower()
    source_key = SOURCE_ALIASES.get(requested_source_key, requested_source_key)
    registry = load_sources_registry()
    if source_key != "all" and source_key not in registry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fonte nao registrada: {payload.source_key}",
        )
    if source_key != "all" and not registry[source_key].enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Fonte registrada, mas desativada no sources_registry.json. "
                "Ative a fonte somente apos validar transformador, credenciais e limites."
            ),
        )

    task = run_massive_ingestion.delay(source_key)
    _record_admin_task_submission(
        task_id=task.id,
        job="massive_ingestion",
        title="Varredura governamental massiva",
        requested_by=current_user["email"],
        metadata={"source_key": source_key},
    )
    return {
        "status": "accepted",
        "job": "massive_ingestion",
        "task_id": task.id,
        "source_key": source_key,
        "requested_by": current_user["email"],
        "message": "Os robos de coleta foram iniciados em segundo plano.",
    }


def _user_payload(user: User) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "active": user.active,
        "mfa_enabled": user.mfa_enabled,
        "roles": sorted(role.name for role in user.roles),
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _suggestion_payload(suggestion: AdminSuggestion) -> dict[str, Any]:
    return {
        "id": str(suggestion.id),
        "title": suggestion.title,
        "description": suggestion.description,
        "category": suggestion.category,
        "priority": suggestion.priority,
        "status": suggestion.status,
        "created_by_email": suggestion.created_by_email,
        "assigned_to_email": suggestion.assigned_to_email,
        "metadata": suggestion.metadata_json,
        "created_at": suggestion.created_at.isoformat() if suggestion.created_at else None,
        "updated_at": suggestion.updated_at.isoformat() if suggestion.updated_at else None,
    }


def _read_blocked_ips() -> list[dict[str, Any]]:
    try:
        raw_entries = redis_client.hgetall(BLOCKED_IPS_KEY)
    except redis.RedisError:
        return []
    entries: list[dict[str, Any]] = []
    for ip_address, raw_value in raw_entries.items():
        try:
            payload = json.loads(raw_value)
        except (TypeError, json.JSONDecodeError):
            payload = {"ip_address": ip_address, "reason": "Registro invalido no Redis."}
        entries.append(payload)
    entries.sort(key=lambda item: str(item.get("blocked_at", "")), reverse=True)
    return entries


def _get_user_or_404(db: Session, user_id: UUID) -> User:
    user = (
        db.query(User)
        .options(selectinload(User.roles))
        .filter(User.id == user_id)
        .one_or_none()
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado.")
    return user


def _get_or_create_role(db: Session, role_name: str) -> Role:
    role = db.query(Role).filter(Role.name == role_name).one_or_none()
    if role is not None:
        return role
    role = Role(name=role_name, description=None)
    db.add(role)
    db.flush()
    return role


def _temporary_password() -> str:
    return f"ONGP-{secrets.token_urlsafe(18)}"


def _request_client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first_hop = forwarded_for.split(",", 1)[0].strip()
        if first_hop:
            return first_hop
    return request.client.host if request.client else None


def _api_health() -> dict[str, Any]:
    return {
        "name": "api",
        "status": "ok",
        "message": "FastAPI online e respondendo.",
        "technical_details": {"component": "fastapi"},
    }


def _load_raw_sources_registry() -> dict[str, Any]:
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Nao foi possivel ler sources_registry.json: {exc}",
        ) from exc


def _write_raw_sources_registry(payload: dict[str, Any]) -> None:
    try:
        REGISTRY_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Nao foi possivel gravar sources_registry.json: {exc}",
        ) from exc


def _source_payload(
    key: str,
    config: SourceConfig,
    raw_source: dict[str, Any],
) -> dict[str, Any]:
    readiness = _source_readiness(raw_source, config)
    return {
        "key": key,
        "name": config.name,
        "enabled": config.enabled,
        "source_type": config.source_type,
        "destination_model": config.destination_model.rsplit(".", 1)[-1],
        "base_url": config.base_url,
        "category": raw_source.get("category") or "sem_categoria",
        "auth_env": readiness["auth_env"],
        "auth_header": config.auth_header or raw_source.get("auth_header"),
        "requires_token": readiness["requires_token"],
        "has_auth_token": readiness["has_auth_token"],
        "can_enable": readiness["can_enable"],
        "activation_notes": readiness["activation_notes"],
        "endpoints": config.endpoints,
    }


def _source_readiness(
    raw_source: dict[str, Any],
    config: SourceConfig,
) -> dict[str, Any]:
    auth_env = config.auth_env or raw_source.get("auth_env")
    requires_token = bool(raw_source.get("requires_token") or auth_env)
    has_auth_token = True
    activation_notes: list[str] = []

    if requires_token and auth_env:
        has_auth_token = bool(getattr(settings, str(auth_env), ""))
        if has_auth_token:
            activation_notes.append(f"Credencial {auth_env} detectada no ambiente.")
        else:
            activation_notes.append(
                f"Configure {auth_env} no .env, no docker-compose ou em GitHub Secrets antes de ativar."
            )
    elif raw_source.get("requires_token") and not auth_env:
        has_auth_token = False
        activation_notes.append(
            "Esta fonte foi marcada como requires_token=true, mas ainda nao possui auth_env/auth_header no registry."
        )

    if config.source_type == "json" and _looks_like_catalog_endpoint(config):
        activation_notes.append(
            "Fonte de catalogo: o conector le metadados de datasets. Para ingerir arquivos internos, crie um transformador especifico."
        )

    if "{id}" in json.dumps(config.endpoints) or "{municipio}" in json.dumps(config.endpoints):
        activation_notes.append(
            "Endpoint possui parametros de caminho. Use somente apos definir valores padrao ou conector especifico."
        )

    if not activation_notes:
        activation_notes.append("Fonte pronta para ativacao operacional.")

    path_params_pending = "{id}" in json.dumps(config.endpoints) or "{municipio}" in json.dumps(config.endpoints)
    can_enable = has_auth_token and not path_params_pending
    return {
        "auth_env": auth_env,
        "requires_token": requires_token,
        "has_auth_token": has_auth_token,
        "can_enable": can_enable,
        "activation_notes": activation_notes,
    }


def _looks_like_catalog_endpoint(config: SourceConfig) -> bool:
    endpoint_text = " ".join(config.endpoints.values()).lower()
    return (
        "package_search" in endpoint_text
        or "swagger" in endpoint_text
        or endpoint_text.endswith("/docs")
    )


def _activation_help() -> dict[str, Any]:
    return {
        "registry_path": _display_registry_path(),
        "env_file": ".env",
        "env_example": ".env.example",
        "github_secrets": [
            "CGU_API_KEY",
            "PORTAL_TRANSPARENCIA_API_KEY",
            "OPENAI_API_KEY",
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "GOVBR_CLIENT_ID",
        ],
        "steps": [
            "1. Verifique a coluna 'Pendencias' da fonte desejada.",
            "2. Se pedir credencial, coloque a chave no .env local, no docker-compose ou em GitHub Secrets com o mesmo nome exibido.",
            "3. Ative a fonte no painel. A alteracao grava o campo enabled em sources_registry.json.",
            "4. Execute 'Iniciar Varredura' com a fonte especifica ou escolha 'Todas as fontes habilitadas'.",
            "5. Acompanhe o Monitor de Logs para validar se houve erro de credencial, endpoint ou parser.",
        ],
        "production_note": (
            "Em Docker/CI, alteracoes feitas pelo painel podem ser temporarias se o container for recriado. "
            "Para tornar permanente, versionar o sources_registry.json atualizado no repositorio."
        ),
    }


def _display_registry_path() -> str:
    try:
        project_root = Path(__file__).resolve().parents[4]
        return str(REGISTRY_PATH.relative_to(project_root))
    except ValueError:
        return str(REGISTRY_PATH)


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
