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

import base64
import binascii
import hashlib
import hmac
import json
import threading
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, fields
from typing import Any

TOKEN_HEADER = "X-Execution-Token"
TOKEN_VERSION = "v1"
ISSUER = "sentinel-gateway"
DEFAULT_TTL_SECONDS = 60
MAX_TTL_SECONDS = 300
MIN_KEY_BYTES = 32
CLOCK_SKEW_SECONDS = 5


class TokenError(Exception):
    """A token could not be issued or did not verify.

    ``code`` is a short machine-readable reason that is safe to return to a caller.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


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


def load_key(secret: str) -> bytes:
    """Turn the shared secret from configuration into a signing key."""
    key = secret.encode("utf-8")
    if len(key) < MIN_KEY_BYTES:
        raise TokenError(
            "key_too_short",
            f"the signing key must be at least {MIN_KEY_BYTES} bytes long",
        )
    return key


def canonical_json(value: Any) -> bytes:
    """Serialize JSON values the same way on every service, so hashes match."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


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
    _check_key(key)
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
    signing_input = f"{TOKEN_VERSION}.{_b64encode(canonical_json(asdict(claims)))}"
    return f"{signing_input}.{_b64encode(_sign(key, signing_input))}"


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
    _check_key(key)
    parts = token.split(".")
    if len(parts) != 3:
        raise TokenError("token_malformed", "the token is not in the expected format")
    version, payload, signature = parts
    if version != TOKEN_VERSION:
        raise TokenError(
            "token_version_unsupported", "the token version is not supported"
        )
    if not hmac.compare_digest(
        _sign(key, f"{version}.{payload}"), _b64decode(signature)
    ):
        raise TokenError("token_signature_invalid", "the token signature is not valid")

    claims = _parse_claims(payload)
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


def _check_key(key: bytes) -> None:
    if len(key) < MIN_KEY_BYTES:
        raise TokenError(
            "key_too_short",
            f"the signing key must be at least {MIN_KEY_BYTES} bytes long",
        )


def _sign(key: bytes, signing_input: str) -> bytes:
    return hmac.new(key, signing_input.encode("ascii"), hashlib.sha256).digest()


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(text: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except (binascii.Error, ValueError) as exc:
        raise TokenError(
            "token_malformed", "the token is not in the expected format"
        ) from exc


def _parse_claims(payload: str) -> TokenClaims:
    try:
        data = json.loads(_b64decode(payload))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TokenError("token_malformed", "the token claims cannot be read") from exc
    if not isinstance(data, dict) or set(data) != set(_CLAIM_TYPES):
        raise TokenError("token_malformed", "the token claims are incomplete")
    for name, expected in _CLAIM_TYPES.items():
        value = data[name]
        if not isinstance(value, expected) or isinstance(value, bool):
            raise TokenError(
                "token_malformed", f"the token claim {name} has the wrong type"
            )
    return TokenClaims(**data)
