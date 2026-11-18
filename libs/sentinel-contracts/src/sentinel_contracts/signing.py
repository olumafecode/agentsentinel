"""Signing primitives shared by execution tokens and session tokens.

A signed token is ``<version>.<payload>.<signature>``. The payload is base64url JSON
claims and the signature is base64url HMAC-SHA256 over ``<version>.<payload>``. Each
token type has its own version prefix and its own key, so a token of one type is
never accepted as the other.
"""

import base64
import binascii
import hashlib
import hmac
import json
from typing import Any

MIN_KEY_BYTES = 32
CLOCK_SKEW_SECONDS = 5


class TokenError(Exception):
    """A token could not be issued or did not verify.

    ``code`` is a short machine-readable reason that is safe to return to a caller.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def load_key(secret: str) -> bytes:
    """Turn a shared secret from configuration into a signing key."""
    key = secret.encode("utf-8")
    check_key(key)
    return key


def check_key(key: bytes) -> None:
    """Raise TokenError when a key is too short to sign with."""
    if len(key) < MIN_KEY_BYTES:
        raise TokenError(
            "key_too_short",
            f"the signing key must be at least {MIN_KEY_BYTES} bytes long",
        )


def canonical_json(value: Any) -> bytes:
    """Serialize JSON values the same way on every service, so hashes and signatures match."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def encode_signed(version: str, claims: dict[str, Any], key: bytes) -> str:
    """Sign ``claims`` and return the token."""
    check_key(key)
    signing_input = f"{version}.{_b64encode(canonical_json(claims))}"
    return f"{signing_input}.{_b64encode(_sign(key, signing_input))}"


def decode_signed(
    token: str, *, version: str, key: bytes, prefix: str
) -> dict[str, Any]:
    """Check a token's format, version and signature, and return its raw claims.

    Error codes start with ``prefix``, for example ``token_signature_invalid``. The
    caller still has to check what the claims say.
    """
    check_key(key)
    parts = token.split(".")
    if not token.isascii() or len(parts) != 3:
        raise TokenError(
            f"{prefix}_malformed", "the token is not in the expected format"
        )
    token_version, payload, signature = parts
    if token_version != version:
        raise TokenError(
            f"{prefix}_version_unsupported", "the token version is not supported"
        )
    expected = _sign(key, f"{token_version}.{payload}")
    if not hmac.compare_digest(expected, _b64decode(signature, prefix)):
        raise TokenError(
            f"{prefix}_signature_invalid", "the token signature is not valid"
        )
    try:
        claims = json.loads(_b64decode(payload, prefix))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TokenError(
            f"{prefix}_malformed", "the token claims cannot be read"
        ) from exc
    if not isinstance(claims, dict):
        raise TokenError(f"{prefix}_malformed", "the token claims are incomplete")
    return claims


def _sign(key: bytes, signing_input: str) -> bytes:
    return hmac.new(key, signing_input.encode("ascii"), hashlib.sha256).digest()


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(text: str, prefix: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except (binascii.Error, ValueError) as exc:
        raise TokenError(
            f"{prefix}_malformed", "the token is not in the expected format"
        ) from exc
