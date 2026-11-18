"""Signed customer session tokens (ADR-012).

When a customer signs in and starts a chat, Veridane's identity service issues a
session token that names the customer, the session, the agent serving them and the
task they asked for. Vera passes it to the gateway with every action, and the gateway
binds the action to what the token says rather than to what the agent claims. Vera
cannot change a session token, because it does not have the signing key.

Format: ``s1.<payload>.<signature>``, signed like an execution token but with its own
key (``SESSION_TOKEN_KEY``) and version prefix, so neither token is accepted as the
other. A session token can be used for many actions until it expires.
"""

import time
from typing import Annotated

from pydantic import Field, StrictInt, StringConstraints, ValidationError

from sentinel_contracts.actions import Contract, TaskType
from sentinel_contracts.identifiers import AgentId, CustomerId, SessionId
from sentinel_contracts.signing import (
    CLOCK_SKEW_SECONDS,
    TokenError,
    decode_signed,
    encode_signed,
)

SESSION_HEADER = "X-Session-Token"
SESSION_TOKEN_VERSION = "s1"
SESSION_ISSUER = "veridane-identity"
SESSION_AUDIENCE = "sentinel-gateway"
DEFAULT_SESSION_TTL_SECONDS = 30 * 60
MAX_SESSION_TTL_SECONDS = 4 * 60 * 60

Channel = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z_]{1,19}$")]


class SessionClaims(Contract):
    """What a verified session token says. The fields match UserSession in the schema."""

    session_id: SessionId
    customer_id: CustomerId = Field(description="The signed-in customer")
    agent_id: AgentId = Field(description="The agent serving this session")
    task_type: TaskType = Field(description="What the customer asked for")
    channel: Channel = Field(description="Where the session runs, for example web_chat")
    issuer: str
    audience: str
    issued_at: StrictInt = Field(description="Unix time the session started")
    expires_at: StrictInt = Field(description="Unix time the session ends")


def issue_session_token(
    *,
    key: bytes,
    session_id: str,
    customer_id: str,
    agent_id: str,
    task_type: TaskType | str,
    channel: str = "web_chat",
    ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
    now: float | None = None,
) -> str:
    """Create a session token. Only the identity service and test tools call this."""
    if not 1 <= ttl_seconds <= MAX_SESSION_TTL_SECONDS:
        raise ValueError(f"ttl_seconds must be between 1 and {MAX_SESSION_TTL_SECONDS}")
    issued_at = int(time.time() if now is None else now)
    claims = SessionClaims(
        session_id=session_id,
        customer_id=customer_id,
        agent_id=agent_id,
        task_type=task_type,
        channel=channel,
        issuer=SESSION_ISSUER,
        audience=SESSION_AUDIENCE,
        issued_at=issued_at,
        expires_at=issued_at + ttl_seconds,
    )
    return encode_signed(SESSION_TOKEN_VERSION, claims.model_dump(mode="json"), key)


def verify_session_token(
    token: str, *, key: bytes, now: float | None = None
) -> SessionClaims:
    """Check a session token and return its claims.

    Raises TokenError, with a code starting ``session_``, when the token is malformed,
    signed with another key, issued by someone else, meant for another service, not
    yet valid or expired.
    """
    raw = decode_signed(token, version=SESSION_TOKEN_VERSION, key=key, prefix="session")
    try:
        claims = SessionClaims.model_validate(raw)
    except ValidationError as exc:
        raise TokenError(
            "session_malformed", "the session claims are incomplete or invalid"
        ) from exc
    current = int(time.time() if now is None else now)
    if claims.issuer != SESSION_ISSUER:
        raise TokenError(
            "session_issuer_invalid", "the session was not issued by Veridane identity"
        )
    if claims.audience != SESSION_AUDIENCE:
        raise TokenError(
            "session_audience_mismatch", "the session is meant for another service"
        )
    if not 0 < claims.expires_at - claims.issued_at <= MAX_SESSION_TTL_SECONDS:
        raise TokenError(
            "session_lifetime_invalid", "the session lifetime is not allowed"
        )
    if claims.issued_at > current + CLOCK_SKEW_SECONDS:
        raise TokenError("session_not_yet_valid", "the session has not started yet")
    if current >= claims.expires_at:
        raise TokenError("session_expired", "the session has expired")
    return claims
