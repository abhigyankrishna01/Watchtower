from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Watchtower"
    environment: str = "development"
    log_level: str = "INFO"

    api_auth_token: str | None = Field(default=None, alias="API_AUTH_TOKEN")
    jwt_secret: str | None = Field(default=None, alias="JWT_SECRET")
    jwt_issuer: str | None = Field(default=None, alias="JWT_ISSUER")
    jwt_audience: str | None = Field(default=None, alias="JWT_AUDIENCE")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(default="redis://localhost:6379/1", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/2", alias="CELERY_RESULT_BACKEND")
    celery_always_eager: bool = Field(default=False, alias="CELERY_ALWAYS_EAGER")
    worker_concurrency: int = Field(default=2, alias="WORKER_CONCURRENCY")
    scheduler_poll_interval_seconds: int = Field(default=30, alias="SCHEDULER_POLL_INTERVAL_SECONDS")

    default_request_timeout: float = Field(default=10.0, alias="DEFAULT_REQUEST_TIMEOUT")
    default_latency_ms_threshold: int = Field(default=1500, alias="DEFAULT_LATENCY_MS_THRESHOLD")

    prometheus_metrics_path: str = Field(default="/metrics", alias="PROMETHEUS_METRICS_PATH")
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")

    result_webhook_url: str | None = Field(default=None, alias="RESULT_WEBHOOK_URL")

    database_url: str = Field(default="sqlite+pysqlite:///./watchtower.db", alias="DATABASE_URL")
    auto_create_db: bool = Field(default=False, alias="AUTO_CREATE_DB")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
