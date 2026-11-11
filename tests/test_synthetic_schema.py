"""Tests for the synthetic data schema (US-15): examples are valid and the synthetic-data rules are enforced."""
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from data.synthetic import models

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = json.loads((ROOT / "data" / "synthetic" / "examples.json").read_text(encoding="utf-8"))
README = (ROOT / "data" / "synthetic" / "README.md").read_text(encoding="utf-8")


def example(name, **changes):
    return {**EXAMPLES[name], **changes}


def test_every_entity_has_an_example():
    assert set(EXAMPLES) == set(models.ENTITIES)


@pytest.mark.parametrize("name", sorted(models.ENTITIES))
def test_example_is_valid(name):
    models.ENTITIES[name].model_validate(EXAMPLES[name])


@pytest.mark.parametrize("name", sorted(models.ENTITIES))
def test_readme_documents_every_field(name):
    assert f"### {name}" in README, f"{name} is missing from data/synthetic/README.md"
    for field in models.ENTITIES[name].model_fields:
        assert f"`{field}`" in README, f"{name}.{field} is missing from data/synthetic/README.md"


@pytest.mark.parametrize(
    ("name", "changes"),
    [
        ("Customer", {"email": "avery.stone@realbank.com"}),  # only reserved example domains are allowed
        ("Customer", {"phone": "+1-312-555-7788"}),  # only the fictional 555-01xx range is allowed
        ("Customer", {"customer_id": "123"}),  # identifiers carry their prefix
        ("Customer", {"national_id": "000-00-0000"}),  # unknown fields, such as government IDs, are rejected
        ("Account", {"currency": "EUR"}),
        ("Account", {"balance": "-1.00"}),
        ("Transaction", {"amount": "0.00"}),
        ("Transaction", {"amount": "-25.00"}),
        ("Transaction", {"transaction_type": "refund", "related_transaction_id": None}),
        ("Agent", {"review_threshold": 0.9, "block_threshold": 0.5}),
        ("UserSession", {"expires_at": "2026-03-14T14:00:00Z"}),
        ("UserSession", {"started_at": "2026-03-14T15:00:00"}),  # timestamps must carry a time zone
        ("ToolCall", {"provenance_labels": {"iban": "untrusted_content"}}),
        ("ToolCall", {"correlation_id": "not-a-uuid"}),
        ("RiskAssessment", {"risk_score": 1.2}),
        ("ApprovalRequest", {"status": "approved", "approver_id": None}),
        ("ApprovalRequest", {"status": "pending"}),  # pending cannot already have an approver
        ("AuditEvent", {"event_hash": "abc"}),
        ("Incident", {"correlation_ids": []}),
        ("ExplanationEvidence", {"evidence_ids": []}),
        ("LabelledActionEvent", {"expected_outcome": "BLOCK", "failure_mode": "none"}),
        ("LabelledActionEvent", {"expected_outcome": "MAYBE"}),
    ],
)
def test_rule_violations_are_rejected(name, changes):
    with pytest.raises(ValidationError):
        models.ENTITIES[name].model_validate(example(name, **changes))


def test_audit_event_hash_follows_the_documented_rule():
    event = dict(EXAMPLES["AuditEvent"])
    stored = event.pop("event_hash")
    canonical = json.dumps(event, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical).hexdigest() == stored


def test_records_cannot_be_changed_after_creation():
    customer = models.Customer.model_validate(EXAMPLES["Customer"])
    with pytest.raises(ValidationError):
        customer.email = "other@example.com"
