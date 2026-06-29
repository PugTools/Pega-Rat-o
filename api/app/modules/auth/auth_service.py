import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.db.database import get_db
from app.db.models import Role, User


MOCK_DEV_TOKEN = "mock-token-ongp"
SYSTEM_ROLES = {
    "public_viewer": "Acesso publico agregado.",
    "analyst": "Consultas detalhadas autorizadas.",
    "auditor": "Alertas, relatorios e evidencias.",
    "source_admin": "Gestao de fontes e coletas.",
    "system_admin": "Usuarios, permissoes e configuracoes.",
    "compliance_officer": "Auditoria, LGPD e retencao.",
}

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def is_development_environment() -> bool:
    return settings.APP_ENV.lower() in {"dev", "development", "local", "test"}


def get_mock_dev_user() -> dict[str, Any]:
    return {
        "id": "dev",
        "email": "dev@ongp.local",
        "name": "ONGP Development User",
        "active": True,
        "roles": ["system_admin", "source_admin", "auditor"],
    }


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return payload


def register_user(
    db: Session,
    email: str,
    password: str,
    name: str | None = None,
) -> dict[str, Any]:
    ensure_system_roles(db)
    normalized_email = email.lower().strip()
    existing_user = _get_user_by_email(db, normalized_email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists.",
        )

    roles = _initial_roles_for_email(db, normalized_email)
    user = User(
        email=normalized_email,
        name=name or normalized_email,
        password_hash=hash_password(password),
        active=True,
        roles=[_get_or_create_role(db, role_name) for role_name in roles],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_to_claims(user)


def authenticate_user(db: Session, email: str, password: str) -> dict[str, Any]:
    user = _get_user_by_email(db, email.lower().strip())
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user.",
        )
    return user_to_claims(user)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    token = _resolve_token(request=request, credentials=credentials)
    if token == MOCK_DEV_TOKEN and is_development_environment():
        logger.debug("accepted_mock_development_token")
        return get_mock_dev_user()

    payload = decode_access_token(token)
    email = payload.get("sub")
    if not isinstance(email, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = _get_user_by_email(db, email.lower().strip())
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user.",
        )

    claims = user_to_claims(user)
    token_roles = payload.get("roles")
    if isinstance(token_roles, list):
        claims["roles"] = sorted({*claims["roles"], *[str(role) for role in token_roles]})
    return claims


def require_any_role(
    current_user: dict[str, Any],
    allowed_roles: set[str],
) -> dict[str, Any]:
    roles = {str(role) for role in current_user.get("roles", [])}
    if not roles.intersection(allowed_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role for this operation.",
        )
    return current_user


def set_auth_cookie(response: Response, token: str) -> None:
    max_age = settings.JWT_EXPIRE_MINUTES * 60
    cookie_kwargs: dict[str, Any] = {
        "key": settings.AUTH_COOKIE_NAME,
        "value": token,
        "max_age": max_age,
        "expires": max_age,
        "path": "/",
        "secure": settings.AUTH_COOKIE_SECURE,
        "httponly": True,
        "samesite": settings.AUTH_COOKIE_SAMESITE,
    }
    if settings.AUTH_COOKIE_DOMAIN:
        cookie_kwargs["domain"] = settings.AUTH_COOKIE_DOMAIN
    response.set_cookie(**cookie_kwargs)


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        path="/",
        domain=settings.AUTH_COOKIE_DOMAIN or None,
    )


def user_to_claims(user: User) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "active": user.active,
        "roles": sorted({role.name for role in user.roles}),
    }


def ensure_system_roles(db: Session) -> None:
    for role_name, description in SYSTEM_ROLES.items():
        role = db.query(Role).filter(Role.name == role_name).one_or_none()
        if role is None:
            db.add(Role(name=role_name, description=description))
    db.commit()


def _resolve_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> str:
    if credentials and credentials.scheme.lower() == "bearer" and credentials.credentials:
        return credentials.credentials

    cookie_token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    if cookie_token:
        return cookie_token

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _get_user_by_email(db: Session, email: str) -> User | None:
    return (
        db.query(User)
        .options(selectinload(User.roles))
        .filter(User.email == email)
        .one_or_none()
    )


def _get_or_create_role(db: Session, role_name: str) -> Role:
    role = db.query(Role).filter(Role.name == role_name).one_or_none()
    if role is not None:
        return role
    role = Role(name=role_name, description=SYSTEM_ROLES.get(role_name))
    db.add(role)
    db.flush()
    return role


def _initial_roles_for_email(db: Session, email: str) -> list[str]:
    if email in settings.system_admin_emails:
        return ["system_admin", "source_admin", "auditor", "analyst"]
    if is_development_environment() and db.query(User).count() == 0:
        return ["system_admin", "source_admin", "auditor", "analyst"]
    return ["analyst"]
