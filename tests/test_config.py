"""Tests for environment parsing and production secret checks."""

import pytest

from directors_rag.config import Settings


def test_comma_delimited_environment_lists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ALLOWED_ORIGINS", "https://one.example, https://two.example")
    monkeypatch.setenv("APP_ALLOWED_HOSTS", "one.example,two.example")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.app_allowed_origins == ["https://one.example", "https://two.example"]
    assert settings.app_allowed_hosts == ["one.example", "two.example"]


def test_production_rejects_development_secrets() -> None:
    settings = Settings(app_env="production")
    with pytest.raises(ValueError, match="non-default"):
        settings.validate_production_secrets()
