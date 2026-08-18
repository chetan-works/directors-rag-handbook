"""Centralized, environment-driven application configuration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and an optional `.env` file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Director's RAG Handbook"
    app_env: str = "development"
    app_api_key: str = "change-me-to-a-long-random-secret"
    app_allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:8501"]
    )
    app_allowed_hosts: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "api", "testserver"]
    )
    log_level: str = "INFO"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "directorsrag"
    minio_secret_key: str = "change-me-minio-secret"
    minio_secure: bool = False
    minio_bucket: str = "director-handbook"

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "director_handbook"

    ollama_url: str = "http://localhost:11434"
    ollama_chat_model: str = "qwen2.5:3b"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = 384

    backend_url: str = "http://localhost:8000"
    source_manifest_path: Path = Path("data/sources.yaml")
    eval_dataset_path: Path = Path("data/eval/golden.jsonl")
    max_upload_mb: int = 25
    request_timeout_seconds: float = 90.0
    retrieval_top_k: int = 6
    relevance_threshold: float = 0.35
    chunk_size: int = 1_200
    chunk_overlap: int = 180

    @field_validator("app_allowed_origins", "app_allowed_hosts", mode="before")
    @classmethod
    def split_csv(cls, value: object) -> object:
        """Accept comma-delimited environment variables as lists."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def max_upload_bytes(self) -> int:
        """Return the configured upload limit in bytes."""
        return self.max_upload_mb * 1024 * 1024

    def validate_production_secrets(self) -> None:
        """Reject known development credentials in non-development environments."""
        if self.app_env.lower() == "production" and (
            self.app_api_key.startswith("change-me")
            or self.minio_secret_key.startswith("change-me")
        ):
            raise ValueError("Production requires non-default API and MinIO secrets")


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance for dependency injection."""
    settings = Settings()
    settings.validate_production_secrets()
    return settings
