"""Settings read from environment variables.

The service refuses to start without a valid signing key, so it can never run in a
state where tool calls are accepted without a gateway token.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from demo_bank_api.seed import DEFAULT_SEED
from sentinel_contracts import TokenError, load_key

AUDIENCE = "demo-bank-api"
MIN_ADMIN_KEY_LENGTH = 16


class ConfigError(RuntimeError):
    """A required setting is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    execution_token_key: bytes = field(repr=False)
    admin_key: str | None = field(default=None, repr=False)
    seed: int = DEFAULT_SEED
    audience: str = AUDIENCE

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if environ is None else environ

        secret = env.get("EXECUTION_TOKEN_KEY", "")
        if not secret:
            raise ConfigError(
                "EXECUTION_TOKEN_KEY is not set; the bank will not start without it"
            )
        try:
            key = load_key(secret)
        except TokenError as exc:
            raise ConfigError(f"EXECUTION_TOKEN_KEY is invalid: {exc}") from exc

        admin_key = env.get("DEMO_ADMIN_KEY") or None
        if admin_key is not None and len(admin_key) < MIN_ADMIN_KEY_LENGTH:
            raise ConfigError(
                f"DEMO_ADMIN_KEY must be at least {MIN_ADMIN_KEY_LENGTH} characters long"
            )

        try:
            seed = int(env.get("BANK_SEED", DEFAULT_SEED))
        except ValueError as exc:
            raise ConfigError("BANK_SEED must be a whole number") from exc

        return cls(execution_token_key=key, admin_key=admin_key, seed=seed)
