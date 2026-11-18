"""Vera's settings (US-17).

Vera knows where the gateway is and holds her own agent key for it. That is all. She
has no bank address, no execution token key and no session key, so she cannot reach a
bank tool except through the gateway (ADR-001), and she cannot make up a customer
session (ADR-012). Settings from the environment that belong to other services are
ignored even when they are present.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

DEFAULT_GATEWAY_URL = "http://localhost:8000"
DEFAULT_AGENT_ID = "AGT-001"
DEFAULT_TIMEOUT_SECONDS = 15.0


class ConfigError(RuntimeError):
    """A required setting is missing or invalid."""


@dataclass(frozen=True)
class VeraSettings:
    gateway_url: str
    agent_key: str = field(repr=False)
    agent_id: str = DEFAULT_AGENT_ID
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        if not self.gateway_url.startswith(("http://", "https://")):
            raise ConfigError("GATEWAY_URL must start with http:// or https://")
        if not self.agent_key:
            raise ConfigError("VERA_AGENT_KEY is not set; Vera cannot call the gateway")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "VeraSettings":
        env = os.environ if environ is None else environ
        return cls(
            gateway_url=env.get("GATEWAY_URL", DEFAULT_GATEWAY_URL),
            agent_key=env.get("VERA_AGENT_KEY", ""),
            agent_id=env.get("VERA_AGENT_ID", DEFAULT_AGENT_ID),
        )
