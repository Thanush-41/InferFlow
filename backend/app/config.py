from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # LLM Providers
    gemini_api_key: str = ""
    openai_api_key: str = ""

    # Database — must be set via environment / .env file
    database_url: str = ""
    database_url_sync: str = ""

    # Redis — must be set via environment / .env file
    redis_url: str = ""

    # App
    app_env: str = "development"

    # CORS — comma-separated list of allowed origins
    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://frontend:3000"

    # SDK defaults — override via env vars (DEFAULT_MODEL, DEFAULT_PROVIDER, etc.)
    default_model: str = "gemini-2.5-flash"
    default_provider: str = "gemini"
    default_openai_model: str = "gpt-4.1"
    preview_max_length: int = 500

    # Ingestion pipeline settings
    redis_queue_key: str = "inference_logs"
    max_context_messages: int = 20

    # Serverless / deployment settings
    # Set SERVERLESS_MODE=true on Vercel (uses NullPool, disables background worker)
    serverless_mode: bool = False
    # Set BACKGROUND_WORKER_ENABLED=false on Vercel (queue drained by cron instead)
    background_worker_enabled: bool = True
    # Set DATABASE_SSL_REQUIRE=true for managed Postgres (Neon, Supabase, RDS, etc.)
    # Also enables statement_cache_size=0 for PgBouncer transaction-mode pooler
    database_ssl_require: bool = False
    # Secret for securing the /api/ingest/process-queue cron endpoint
    cron_secret: str = ""

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
