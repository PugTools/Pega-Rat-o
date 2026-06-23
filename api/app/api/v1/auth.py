import os
from urllib.parse import urlencode

from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, HTTPException, status

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
        "client_id_env": "GOOGLE_CLIENT_ID",
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

    client_id = os.getenv(config["client_id_env"], f"mock-{provider}-client")
    redirect_uri = os.getenv(
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
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(status_code=404, detail="OAuth provider not configured.")
    if not code:
        raise HTTPException(status_code=400, detail="Missing OAuth authorization code.")

    email = f"{provider}.mock.user@ongp.local"
    if email not in fake_users_db:
        register_user(email=email, password=f"{provider}-oauth-placeholder", name=f"{provider} OAuth User")
    token = create_access_token(subject=email, extra_claims={"provider": provider, "state": state})
    return TokenResponse(access_token=token)
