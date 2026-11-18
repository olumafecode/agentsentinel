"""Signed single-use execution tokens (ADR-010).

The gateway issues a token only for an action it allows. The token is bound to one
correlation ID, one tool, the exact arguments (by SHA-256) and one customer, and it
expires after a short time. A protected tool runs only when the token verifies and
has not been used before, so an agent cannot call a bank tool on its own and a
captured token cannot be replayed or reused with different arguments.

Format: ``v1.<payload>.<signature>``. The payload is base64url JSON claims; the
signature is base64url HMAC-SHA256 over ``v1.<payload>`` with a key shared by the
gateway and the bank and never given to the agent.
"""

import hashlib
import hmac
import threading
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, fields
from typing import Any

from sentinel_contracts.signing import (
    CLOCK_SKEW_SECONDS,
    MIN_KEY_BYTES,
    TokenError,
    canonical_json,
    decode_signed,
    encode_signed,
    load_key,
)

__all__ = [
    "CLOCK_SKEW_SECONDS",
    "DEFAULT_TTL_SECONDS",
    "ISSUER",
    "MAX_TTL_SECONDS",
    "MIN_KEY_BYTES",
    "TOKEN_HEADER",
    "TOKEN_VERSION",
    "ReplayGuard",
    "TokenClaims",
    "TokenError",
    "arguments_digest",
    "canonical_json",
    "issue_token",
    "load_key",
    "verify_token",
]

TOKEN_HEADER = "X-Execution-Token"
TOKEN_VERSION = "v1"
ISSUER = "sentinel-gateway"
DEFAULT_TTL_SECONDS = 60
MAX_TTL_SECONDS = 300


@dataclass(frozen=True, slots=True)
class TokenClaims:
    """What a verified token says about the action it allows."""

    token_id: str
    correlation_id: str
    tool_name: str
    arguments_sha256: str
    customer_scope: str
    issuer: str
    audience: str
    issued_at: int
    expires_at: int


_CLAIM_TYPES = {
    f.name: (int if f.type in (int, "int") else str) for f in fields(TokenClaims)
}


def arguments_digest(arguments: Mapping[str, Any]) -> str:
    """SHA-256 of the tool arguments in canonical JSON form."""
    return hashlib.sha256(canonical_json(dict(arguments))).hexdigest()


def issue_token(
    *,
    key: bytes,
    correlation_id: str,
    tool_name: str,
    arguments: Mapping[str, Any],
    customer_scope: str,
    audience: str,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    now: float | None = None,
) -> str:
    """Create a token that allows exactly one call of ``tool_name`` with ``arguments``."""
    if not 1 <= ttl_seconds <= MAX_TTL_SECONDS:
        raise ValueError(f"ttl_seconds must be between 1 and {MAX_TTL_SECONDS}")
    issued_at = int(time.time() if now is None else now)
    claims = TokenClaims(
        token_id=uuid.uuid4().hex,
        correlation_id=correlation_id,
        tool_name=tool_name,
        arguments_sha256=arguments_digest(arguments),
        customer_scope=customer_scope,
        issuer=ISSUER,
        audience=audience,
        issued_at=issued_at,
        expires_at=issued_at + ttl_seconds,
    )
    return encode_signed(TOKEN_VERSION, asdict(claims), key)


def verify_token(
    token: str,
    *,
    key: bytes,
    audience: str,
    tool_name: str,
    arguments: Mapping[str, Any],
    now: float | None = None,
) -> TokenClaims:
    """Check a token against the call it arrived with and return its claims.

    Raises TokenError when the token is malformed, signed with another key, expired,
    meant for another service or tool, or issued for different arguments. It does
    not check reuse; pass the claims to a ReplayGuard for that.
    """
    claims = _parse_claims(
        decode_signed(token, version=TOKEN_VERSION, key=key, prefix="token")
    )
    current = int(time.time() if now is None else now)
    if claims.issuer != ISSUER:
        raise TokenError(
            "token_issuer_invalid", "the token was not issued by the gateway"
        )
    if claims.audience != audience:
        raise TokenError(
            "token_audience_mismatch", "the token is meant for another service"
        )
    if not 0 < claims.expires_at - claims.issued_at <= MAX_TTL_SECONDS:
        raise TokenError("token_lifetime_invalid", "the token lifetime is not allowed")
    if claims.issued_at > current + CLOCK_SKEW_SECONDS:
        raise TokenError("token_not_yet_valid", "the token is not valid yet")
    if current >= claims.expires_at:
        raise TokenError("token_expired", "the token has expired")
    if claims.tool_name != tool_name:
        raise TokenError("token_tool_mismatch", "the token was issued for another tool")
    if not hmac.compare_digest(claims.arguments_sha256, arguments_digest(arguments)):
        raise TokenError(
            "token_arguments_mismatch",
            "the arguments differ from the ones that were allowed",
        )
    return claims


class ReplayGuard:
    """Remembers used token IDs until they expire, so each token works only once.

    The memory is per process. A service that runs more than one replica must share
    this record (for example in PostgreSQL) before it scales out.
    """

    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock
        self._used: dict[str, int] = {}
        self._lock = threading.Lock()

    def consume(self, claims: TokenClaims) -> None:
        """Mark the token as used, or raise TokenError if it was used before."""
        now = self._clock()
        with self._lock:
            expired = [
                token_id for token_id, until in self._used.items() if until <= now
            ]
            for token_id in expired:
                del self._used[token_id]
            if claims.token_id in self._used:
                raise TokenError("token_replayed", "the token has already been used")
            self._used[claims.token_id] = claims.expires_at

    def __len__(self) -> int:
        with self._lock:
            return len(self._used)


def _parse_claims(data: dict[str, Any]) -> TokenClaims:
    if set(data) != set(_CLAIM_TYPES):
        raise TokenError("token_malformed", "the token claims are incomplete")
    for name, expected in _CLAIM_TYPES.items():
        value = data[name]
        if not isinstance(value, expected) or isinstance(value, bool):
            raise TokenError(
                "token_malformed", f"the token claim {name} has the wrong type"
            )
    return TokenClaims(**data)
