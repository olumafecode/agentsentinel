"""Settings read from environment variables.

The gateway refuses to start without its keys, so it never runs in a state where it
could sign execution tokens or accept sessions with a missing or weak key.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from sentinel_contracts import TokenError, load_key
from sentinel_gateway.auth import AgentKeyring
from sentinel_gateway.bank import DEFAULT_TIMEOUT_SECONDS

DEFAULT_BANK_URL = "http://localhost:8001"
BANK_AUDIENCE = "demo-bank-api"


class ConfigError(RuntimeError):
    """A required setting is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    execution_token_key: bytes = field(repr=False)
    session_token_key: bytes = field(repr=False)
    agent_keys: AgentKeyring
    bank_url: str = DEFAULT_BANK_URL
    bank_timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    bank_audience: str = BANK_AUDIENCE

    def __post_init__(self) -> None:
        if self.execution_token_key == self.session_token_key:
            raise ConfigError(
                "EXECUTION_TOKEN_KEY and SESSION_TOKEN_KEY must be different keys"
            )
        if not self.bank_url.startswith(("http://", "https://")):
            raise ConfigError("BANK_URL must start with http:// or https://")
        if not 0 < self.bank_timeout_seconds <= 60:
            raise ConfigError("BANK_TIMEOUT_SECONDS must be between 0 and 60")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if environ is None else environ
        execution_key = _signing_key(env, "EXECUTION_TOKEN_KEY")
        session_key = _signing_key(env, "SESSION_TOKEN_KEY")

        agent_keys = env.get("AGENT_KEYS", "")
        if not agent_keys:
            raise ConfigError(
                "AGENT_KEYS is not set; no agent could call the gateway without it"
            )
        try:
            keyring = AgentKeyring.parse(agent_keys)
        except ValueError as exc:
            raise ConfigError(f"AGENT_KEYS is invalid: {exc}") from exc

        try:
            timeout = float(env.get("BANK_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))
        except ValueError as exc:
            raise ConfigError("BANK_TIMEOUT_SECONDS must be a number") from exc

        return cls(
            execution_token_key=execution_key,
            session_token_key=session_key,
            agent_keys=keyring,
            bank_url=env.get("BANK_URL", DEFAULT_BANK_URL),
            bank_timeout_seconds=timeout,
        )


def _signing_key(env: Mapping[str, str], name: str) -> bytes:
    secret = env.get(name, "")
    if not secret:
        raise ConfigError(f"{name} is not set; the gateway will not start without it")
    try:
        return load_key(secret)
    except TokenError as exc:
        raise ConfigError(f"{name} is invalid: {exc}") from exc
