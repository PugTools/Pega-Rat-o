from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: str = "development"
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,https://localhost:3000,https://127.0.0.1:3000"
    CORS_ALLOWED_ORIGIN_REGEX: str = r"https://.*\.(app\.github\.dev|github\.dev|githubpreview\.dev)"
    TRUSTED_HOSTS: str = "localhost,127.0.0.1,testserver,api,ongp-api,web,ongp-web,*.github.dev,*.app.github.dev,*.githubpreview.dev"
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_MAX_REQUESTS: int = 240
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_BURST_MAX_REQUESTS: int = 40
    RATE_LIMIT_BURST_WINDOW_SECONDS: int = 10
    MAX_REQUEST_BODY_BYTES: int = 2_000_000
    SECURITY_HSTS_ENABLED: bool = True
    SECURITY_HSTS_MAX_AGE_SECONDS: int = 31536000
    SYSTEM_ADMIN_EMAILS: str = ""
    ADMIN_BOOTSTRAP_EMAIL: str = ""
    ADMIN_BOOTSTRAP_PASSWORD: str = ""
    ADMIN_BOOTSTRAP_RESET_PASSWORD: bool = False
    JWT_SECRET_KEY: str = "ongp-local-dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    AUTH_COOKIE_NAME: str = "ongp_token"
    AUTH_COOKIE_SECURE: bool = False
    AUTH_COOKIE_SAMESITE: str = "lax"
    AUTH_COOKIE_DOMAIN: str = ""
    CGU_API_KEY: str = ""
    PORTAL_TRANSPARENCIA_API_KEY: str = ""
    DB_URL: str = "postgresql+psycopg://ongp_user:ongp_password@localhost:5432/ongp"
    DATABASE_URL: str | None = None
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "ongp_password"
    NEO4J_DATABASE: str = "neo4j"
    REDIS_URL: str = "redis://localhost:6379/0"
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    HTTP_VERIFY_SSL: bool = True
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/oauth/google/callback"
    GOVBR_CLIENT_ID: str = ""
    GOVBR_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/oauth/govbr/callback"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        return self.DATABASE_URL or self.DB_URL

    @property
    def portal_transparencia_api_key(self) -> str:
        return self.CGU_API_KEY or self.PORTAL_TRANSPARENCIA_API_KEY

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [
            item.strip()
            for item in self.CORS_ALLOWED_ORIGINS.split(",")
            if item.strip()
        ]

    @property
    def cors_allowed_origin_regex(self) -> str | None:
        value = self.CORS_ALLOWED_ORIGIN_REGEX.strip()
        return value or None

    @property
    def trusted_hosts(self) -> list[str]:
        return [
            item.strip()
            for item in self.TRUSTED_HOSTS.split(",")
            if item.strip()
        ]

    @property
    def system_admin_emails(self) -> set[str]:
        return {
            item.strip().lower()
            for item in self.SYSTEM_ADMIN_EMAILS.split(",")
            if item.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
