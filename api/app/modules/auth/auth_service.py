import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


SECRET_KEY = os.getenv("JWT_SECRET_KEY", "ongp-local-dev-secret-change-me")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
MOCK_DEV_TOKEN = "mock-token-ongp"
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

fake_users_db: dict[str, dict[str, Any]] = {}


def is_development_environment() -> bool:
    return settings.APP_ENV.lower() in {"dev", "development", "local", "test"}


def get_mock_dev_user() -> dict[str, Any]:
    return {
        "email": "dev@ongp.local",
        "name": "ONGP Development User",
        "active": True,
        "roles": ["admin"],
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
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return payload


def register_user(email: str, password: str, name: str | None = None) -> dict[str, Any]:
    normalized_email = email.lower().strip()
    if normalized_email in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists.",
        )

    user = {
        "email": normalized_email,
        "name": name or normalized_email,
        "hashed_password": hash_password(password),
        "active": True,
    }
    fake_users_db[normalized_email] = user
    return user


def authenticate_user(email: str, password: str) -> dict[str, Any]:
    normalized_email = email.lower().strip()
    user = fake_users_db.get(normalized_email)
    if user is None or not verify_password(password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
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

    user = fake_users_db.get(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.get("active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user.",
        )
    return user
