"""The bank refuses to start without a valid signing key (fail closed)."""

import pytest

from demo_bank_api.config import ConfigError, Settings
from demo_bank_api.main import create_app
from demo_bank_api.seed import DEFAULT_SEED

KEY = "a-signing-key-that-is-long-enough-0123456789"


def test_settings_come_from_the_environment():
    settings = Settings.from_env(
        {
            "EXECUTION_TOKEN_KEY": KEY,
            "DEMO_ADMIN_KEY": "admin-key-0123456789",
            "BANK_SEED": "7",
        }
    )
    assert settings.execution_token_key == KEY.encode()
    assert settings.admin_key == "admin-key-0123456789"
    assert settings.seed == 7


def test_defaults_apply_when_optional_settings_are_missing():
    settings = Settings.from_env({"EXECUTION_TOKEN_KEY": KEY})
    assert settings.admin_key is None
    assert settings.seed == DEFAULT_SEED


@pytest.mark.parametrize(
    "environ",
    [
        {},
        {"EXECUTION_TOKEN_KEY": ""},
        {"EXECUTION_TOKEN_KEY": "too-short"},
        {"EXECUTION_TOKEN_KEY": KEY, "DEMO_ADMIN_KEY": "short"},
        {"EXECUTION_TOKEN_KEY": KEY, "BANK_SEED": "twenty"},
    ],
)
def test_invalid_settings_stop_the_bank_from_starting(environ):
    with pytest.raises(ConfigError):
        Settings.from_env(environ)


def test_create_app_reads_the_environment(monkeypatch):
    monkeypatch.delenv("EXECUTION_TOKEN_KEY", raising=False)
    with pytest.raises(ConfigError):
        create_app()
    monkeypatch.setenv("EXECUTION_TOKEN_KEY", KEY)
    assert create_app().title == "AgentSentinel demo bank API"


def test_secrets_are_not_shown_in_logs_or_errors():
    settings = Settings.from_env(
        {"EXECUTION_TOKEN_KEY": KEY, "DEMO_ADMIN_KEY": "admin-key-0123456789"}
    )
    assert KEY not in repr(settings)
    assert "admin-key" not in repr(settings)
