"""Settings and agent keys: the gateway will not start in an unsafe state."""

import pytest

from sentinel_gateway.auth import AgentKeyring, bearer_credentials
from sentinel_gateway.config import DEFAULT_BANK_URL, ConfigError, Settings

EXECUTION = "execution-key-from-the-environment-0123456789"
SESSION = "session-key-from-the-environment-0123456789ab"
VERA = "vera-key-from-the-environment-0123456789abcd"
ATLAS = "atlas-key-from-the-environment-0123456789abc"

ENV = {
    "EXECUTION_TOKEN_KEY": EXECUTION,
    "SESSION_TOKEN_KEY": SESSION,
    "AGENT_KEYS": f"AGT-001:{VERA}",
}


def test_settings_are_read_from_the_environment():
    settings = Settings.from_env(
        {
            **ENV,
            "AGENT_KEYS": f" AGT-001:{VERA} , AGT-002:{ATLAS},",
            "BANK_URL": "https://bank.internal:8443",
            "BANK_TIMEOUT_SECONDS": "2.5",
        }
    )

    assert settings.execution_token_key == EXECUTION.encode()
    assert settings.session_token_key == SESSION.encode()
    assert settings.agent_keys.agent_ids == {"AGT-001", "AGT-002"}
    assert settings.bank_url == "https://bank.internal:8443"
    assert settings.bank_timeout_seconds == 2.5


def test_the_bank_url_has_a_local_default():
    assert Settings.from_env(ENV).bank_url == DEFAULT_BANK_URL


def test_keys_never_appear_in_the_settings_repr():
    text = repr(Settings.from_env(ENV))

    assert EXECUTION not in text
    assert SESSION not in text
    assert VERA not in text
    assert "AGT-001" in text


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"EXECUTION_TOKEN_KEY": ""}, "EXECUTION_TOKEN_KEY is not set"),
        ({"SESSION_TOKEN_KEY": "short"}, "SESSION_TOKEN_KEY is invalid"),
        ({"SESSION_TOKEN_KEY": EXECUTION}, "must be different keys"),
        ({"AGENT_KEYS": ""}, "AGENT_KEYS is not set"),
        ({"AGENT_KEYS": "AGT-001"}, "AGENT_KEYS is invalid"),
        ({"AGENT_KEYS": "AGT-001:short"}, "at least 32 characters"),
        ({"AGENT_KEYS": f"vera:{VERA}"}, "not an agent ID"),
        ({"AGENT_KEYS": f"AGT-001:{VERA},AGT-001:{ATLAS}"}, "more than one key"),
        ({"AGENT_KEYS": f"AGT-001:{VERA},AGT-002:{VERA}"}, "its own key"),
        ({"BANK_URL": "bank:8001"}, "BANK_URL must start with"),
        ({"BANK_TIMEOUT_SECONDS": "soon"}, "must be a number"),
        ({"BANK_TIMEOUT_SECONDS": "0"}, "between 0 and 60"),
        ({"BANK_TIMEOUT_SECONDS": "nan"}, "between 0 and 60"),
    ],
)
def test_missing_or_unsafe_settings_stop_the_gateway(change, message):
    with pytest.raises(ConfigError, match=message):
        Settings.from_env({**ENV, **change})


def test_an_agent_is_identified_by_its_key():
    keyring = AgentKeyring({"AGT-001": VERA, "AGT-002": ATLAS})

    assert keyring.authenticate(VERA) == "AGT-001"
    assert keyring.authenticate(ATLAS) == "AGT-002"
    assert keyring.authenticate(VERA + "x") is None
    assert keyring.authenticate("") is None


def test_the_keyring_needs_at_least_one_agent():
    with pytest.raises(ValueError, match="at least one"):
        AgentKeyring({})


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, None),
        ("", None),
        ("Bearer abc", "abc"),
        ("bearer  abc ", "abc"),
        ("Basic abc", None),
        ("Bearer", None),
    ],
)
def test_the_key_is_read_from_a_bearer_header(header, expected):
    assert bearer_credentials(header) == expected
