from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Server
    debug: bool = True
    secret_key: str = "your-secret-key-change-this"

    # Database (Postgres)
    database_url: str = "postgresql+psycopg2://meridian:meridian@postgres:5432/meridian"
    database_async_url: str = "postgresql+asyncpg://meridian:meridian@postgres:5432/meridian"

    # Redis
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"
    embedding_cache_ttl_seconds: int = 60 * 60 * 24

    # Anthropic API
    anthropic_api_key: str = ""
    # Dev/test-only: skip the real Anthropic call, return a deterministic
    # fake completion instead. Token counts are still computed for real via
    # tiktoken on whatever the pipeline actually sends, so cost/routing/
    # truncation math stays honest - only the completion text is fake.
    # Never enable this in production.
    mock_anthropic: bool = False

    # OAuth (Google)
    google_client_id: str = ""
    google_client_secret: str = ""
    oauth_redirect_uri: str = "http://localhost:8000/auth/callback"

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Optimization Settings
    context_truncation_enabled: bool = True
    model_routing_enabled: bool = True
    batch_processing_enabled: bool = True
    quality_threshold: float = 8.5  # 0-10 scale, matches ModelRouter.QUALITY_SCORES
    context_relevance_threshold: float = 0.7
    preserve_recent_messages: int = 5

    # Logging
    log_level: str = "INFO"

    # Claude Model Pricing ($ per 1M tokens)
    claude_opus_input_price: float = 15.0
    claude_opus_output_price: float = 75.0
    claude_sonnet_input_price: float = 3.0
    claude_sonnet_output_price: float = 15.0
    claude_haiku_input_price: float = 0.80
    claude_haiku_output_price: float = 4.0

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
