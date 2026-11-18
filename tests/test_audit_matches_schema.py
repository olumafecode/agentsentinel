"""The audit store writes the AuditEvent entity of the synthetic schema, and nothing else."""

import json
from datetime import datetime
from pathlib import Path

from data.synthetic import models
from sentinel_audit.events import StoredEvent
from sentinel_audit.migrate import pending_migrations
from sentinel_contracts import AuditEventType, Decision

EXAMPLES = json.loads(
    (
        Path(__file__).resolve().parents[1] / "data" / "synthetic" / "examples.json"
    ).read_text(encoding="utf-8")
)


def test_a_stored_event_has_exactly_the_audit_event_fields():
    example = EXAMPLES["AuditEvent"]
    event = StoredEvent(
        position=1,
        **{**example, "created_at": datetime.fromisoformat(example["created_at"])},
    )

    assert set(event.fields()) == set(models.AuditEvent.model_fields)
    assert (
        models.AuditEvent.model_validate(event.fields()).event_hash
        == event.computed_hash()
    )


def test_the_database_accepts_every_event_type_and_decision():
    sql = "\n".join(script for _, script in pending_migrations())

    for value in [*AuditEventType, *Decision]:
        assert f"'{value.value}'" in sql
