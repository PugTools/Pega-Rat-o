from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_ENV: str = "development"
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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
