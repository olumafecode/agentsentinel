"""Agent credentials (FR-02).

Each agent calls the gateway with its own API key in ``Authorization: Bearer <key>``.
The gateway knows the keys only as SHA-256 hashes and works out the agent's identity
from the key, so an agent cannot act under another agent's ID.

Keys come from the AGENT_KEYS setting as ``AGT-001:<key>``, with a comma between
agents. Create a key with ``python -m sentinel_gateway new-key``.
"""

import hashlib
import hmac
import re
from collections.abc import Mapping
from typing import Self

MIN_AGENT_KEY_LENGTH = 32

_AGENT_ID = re.compile(r"^AGT-\d{3}$")


class AgentKeyring:
    """Hashes of the agents' API keys, by agent ID."""

    def __init__(self, keys: Mapping[str, str]) -> None:
        if not keys:
            raise ValueError("at least one agent key is needed")
        digests: dict[str, bytes] = {}
        for agent_id, secret in keys.items():
            if not _AGENT_ID.match(agent_id):
                raise ValueError(f"{agent_id!r} is not an agent ID such as AGT-001")
            if len(secret) < MIN_AGENT_KEY_LENGTH:
                raise ValueError(
                    f"the key for {agent_id} must be at least "
                    f"{MIN_AGENT_KEY_LENGTH} characters long"
                )
            digests[agent_id] = _digest(secret)
        if len(set(digests.values())) != len(digests):
            raise ValueError("each agent needs its own key")
        self._digests = digests

    @classmethod
    def parse(cls, text: str) -> Self:
        """Read ``AGT-001:<key>,AGT-002:<key>``."""
        keys: dict[str, str] = {}
        for item in filter(None, (part.strip() for part in text.split(","))):
            agent_id, separator, secret = item.partition(":")
            agent_id, secret = agent_id.strip(), secret.strip()
            if not separator or not secret:
                raise ValueError("each entry must look like AGT-001:<key>")
            if agent_id in keys:
                raise ValueError(f"{agent_id} has more than one key")
            keys[agent_id] = secret
        return cls(keys)

    @property
    def agent_ids(self) -> frozenset[str]:
        return frozenset(self._digests)

    def authenticate(self, presented: str) -> str | None:
        """Return the ID of the agent that owns this key, or None."""
        digest = _digest(presented)
        owner = None
        for agent_id, expected in self._digests.items():
            if hmac.compare_digest(digest, expected):
                owner = agent_id
        return owner

    def __repr__(self) -> str:
        return f"AgentKeyring({', '.join(sorted(self._digests))})"


def bearer_credentials(authorization: str | None) -> str | None:
    """The key from an ``Authorization: Bearer <key>`` header, or None."""
    if not authorization:
        return None
    scheme, _, credentials = authorization.strip().partition(" ")
    if scheme.lower() != "bearer" or not credentials.strip():
        return None
    return credentials.strip()


def _digest(secret: str) -> bytes:
    return hashlib.sha256(secret.encode("utf-8")).digest()
