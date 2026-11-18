"""Vera holds the gateway address and her own agent key, and nothing for the bank (US-17)."""

from dataclasses import fields

import pytest

from banking_agent.config import DEFAULT_GATEWAY_URL, ConfigError, VeraSettings

KEY = "vera-agent-key-0123456789abcdef0123456"
EVERYTHING_IN_THE_STACK = {
    "GATEWAY_URL": "http://gateway:8000",
    "VERA_AGENT_KEY": KEY,
    "BANK_URL": "http://demo-bank:8001",
    "EXECUTION_TOKEN_KEY": "bank-signing-key-0123456789abcdefghijkl",
    "SESSION_TOKEN_KEY": "session-signing-key-0123456789abcdefghij",
    "DEMO_ADMIN_KEY": "admin-key-0123456789",
}


def test_vera_has_no_setting_for_the_bank_or_any_signing_key():
    names = {field.name for field in fields(VeraSettings)}

    assert names == {"gateway_url", "agent_key", "agent_id", "timeout_seconds"}
    assert not any("bank" in name or "token" in name for name in names)


def test_settings_from_other_services_are_ignored():
    settings = VeraSettings.from_env(EVERYTHING_IN_THE_STACK)

    values = {getattr(settings, field.name) for field in fields(VeraSettings)}
    assert settings.gateway_url == "http://gateway:8000"
    assert settings.agent_key == KEY
    assert "http://demo-bank:8001" not in values
    assert EVERYTHING_IN_THE_STACK["EXECUTION_TOKEN_KEY"] not in values
    assert EVERYTHING_IN_THE_STACK["SESSION_TOKEN_KEY"] not in values


def test_the_gateway_address_has_a_local_default():
    assert (
        VeraSettings.from_env({"VERA_AGENT_KEY": KEY}).gateway_url
        == DEFAULT_GATEWAY_URL
    )


def test_the_agent_key_is_kept_out_of_the_repr():
    assert KEY not in repr(VeraSettings.from_env({"VERA_AGENT_KEY": KEY}))


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({}, "VERA_AGENT_KEY is not set"),
        (
            {"VERA_AGENT_KEY": KEY, "GATEWAY_URL": "gateway:8000"},
            "must start with http",
        ),
    ],
)
def test_vera_will_not_start_without_a_usable_gateway(env, message):
    with pytest.raises(ConfigError, match=message):
        VeraSettings.from_env(env)
