from urllib.parse import urlencode

import httpx
from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.modules.auth.auth_service import (
    authenticate_user,
    create_access_token,
    fake_users_db,
    register_user,
)


router = APIRouter(prefix="/auth", tags=["auth"])


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    email: EmailStr
    name: str
    active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


OAUTH_PROVIDERS = {
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "client_id_env": "GOOGLE_CLIENT_ID",
        "client_secret_env": "GOOGLE_CLIENT_SECRET",
        "redirect_uri_env": "GOOGLE_REDIRECT_URI",
        "scope": "openid email profile",
    },
    "govbr": {
        "authorize_url": "https://sso.acesso.gov.br/authorize",
        "client_id_env": "GOVBR_CLIENT_ID",
        "redirect_uri_env": "GOVBR_REDIRECT_URI",
        "scope": "openid email profile",
    },
}


def _setting_value(name: str, fallback: str = "") -> str:
    value = getattr(settings, name, "")
    return str(value or fallback)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate) -> dict:
    user = register_user(
        email=str(payload.email),
        password=payload.password,
        name=payload.name,
    )
    return {
        "email": user["email"],
        "name": user["name"],
        "active": user["active"],
    }


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    user = authenticate_user(str(payload.email), payload.password)
    token = create_access_token(subject=user["email"], extra_claims={"name": user["name"]})
    return TokenResponse(access_token=token)


@router.get("/oauth/{provider}/authorize")
def oauth_authorize(provider: str) -> dict[str, str]:
    config = OAUTH_PROVIDERS.get(provider)
    if config is None:
        raise HTTPException(status_code=404, detail="OAuth provider not configured.")

    client_id = _setting_value(config["client_id_env"], f"mock-{provider}-client")
    redirect_uri = _setting_value(
        config["redirect_uri_env"],
        f"http://localhost:8000/api/v1/auth/oauth/{provider}/callback",
    )
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": config["scope"],
            "state": "ongp-local-state",
        }
    )
    return {"provider": provider, "authorization_url": f"{config['authorize_url']}?{query}"}


@router.get("/oauth/{provider}/callback", response_model=TokenResponse)
def oauth_callback(provider: str, code: str | None = None, state: str | None = None) -> TokenResponse:
    config = OAUTH_PROVIDERS.get(provider)
    if config is None:
        raise HTTPException(status_code=404, detail="OAuth provider not configured.")
    if not code:
        raise HTTPException(status_code=400, detail="Missing OAuth authorization code.")

    email = _resolve_oauth_email(provider, config, code)
    if email not in fake_users_db:
        register_user(email=email, password=f"{provider}-oauth-placeholder", name=f"{provider} OAuth User")
    token = create_access_token(subject=email, extra_claims={"provider": provider, "state": state})
    return TokenResponse(access_token=token)


def _resolve_oauth_email(provider: str, config: dict[str, str], code: str) -> str:
    if provider != "google":
        return f"{provider}.mock.user@ongp.local"

    client_id = _setting_value(config["client_id_env"])
    client_secret = _setting_value(config["client_secret_env"])
    redirect_uri = _setting_value(config["redirect_uri_env"])
    if not client_id or not client_secret or not redirect_uri:
        return f"{provider}.mock.user@ongp.local"

    try:
        with httpx.Client(timeout=15.0) as client:
            token_response = client.post(
                config["token_url"],
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_response.raise_for_status()
            access_token = token_response.json().get("access_token")
            if not access_token:
                raise HTTPException(status_code=502, detail="Google OAuth token response without access token.")

            userinfo_response = client.get(
                config["userinfo_url"],
                headers={"Authorization": f"Bearer {access_token}"},
            )
            userinfo_response.raise_for_status()
            email = userinfo_response.json().get("email")
            if not email:
                raise HTTPException(status_code=502, detail="Google OAuth userinfo response without email.")
            return str(email)
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Google OAuth exchange failed: {exc}") from exc
