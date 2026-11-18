"""Stored audit events and the audit hash rule (data/synthetic/README.md).

1. Take every field of the event except ``event_hash``.
2. Write them as JSON with keys sorted and no extra spaces.
3. ``event_hash`` is the SHA-256 of that text. The first event uses 64 zeros as
   ``previous_event_hash``.

A stored event is read back exactly as it is in the database, without validation, so
that the chain can still be checked when someone has changed a row by hand.
"""

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

GENESIS_HASH = "0" * 64
"""previous_event_hash of the first event in the chain."""
MAX_POSITION = 999_999
"""Event IDs have six digits (EVT-000001), so the chain holds at most this many events."""


def event_id_for(position: int) -> str:
    """The event ID at a position in the chain: 1 is EVT-000001."""
    if not 1 <= position <= MAX_POSITION:
        raise ValueError(f"the audit chain holds at most {MAX_POSITION} events")
    return f"EVT-{position:06d}"


def timestamp_text(moment: datetime) -> str:
    """A UTC time as ISO 8601 with a Z, the way the schema examples write it."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")


def event_hash(fields: Mapping[str, Any]) -> str:
    """SHA-256 of every field except event_hash, as JSON with sorted keys and no spaces."""
    content = {name: value for name, value in fields.items() if name != "event_hash"}
    text = json.dumps(content, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class StoredEvent:
    """One row of audit.events, in the shape of the AuditEvent entity in the schema."""

    position: int
    event_id: str
    correlation_id: str
    event_type: str
    actor: str
    decision: str | None
    policy_version: str | None
    model_version: str | None
    payload: Any
    created_at: datetime
    previous_event_hash: str
    event_hash: str

    def fields(self) -> dict[str, Any]:
        """The event as JSON values, as the hash rule and the schema see it."""
        return {
            "event_id": self.event_id,
            "correlation_id": self.correlation_id,
            "event_type": self.event_type,
            "actor": self.actor,
            "decision": self.decision,
            "policy_version": self.policy_version,
            "model_version": self.model_version,
            "payload": self.payload,
            "created_at": timestamp_text(self.created_at),
            "previous_event_hash": self.previous_event_hash,
            "event_hash": self.event_hash,
        }

    def computed_hash(self) -> str:
        """What event_hash should be for the content as it is now."""
        return event_hash(self.fields())
