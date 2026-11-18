"""Decision precedence, deny by default and failing closed (US-18.3, ADR-012)."""

import uuid
from datetime import UTC, datetime

import pytest

from sentinel_contracts import Decision, ProtectedActionRequest, ReasonCode
from sentinel_gateway.checks import (
    NO_OBJECTION,
    ActionContext,
    Check,
    Finding,
    Stage,
    objection,
)
from sentinel_gateway.orchestrator import (
    ALLOW_SUMMARY,
    Orchestrator,
    combine,
    invalid_request_verdict,
)

RECEIVED = datetime(2027, 1, 15, 8, 0, tzinfo=UTC)

REQUEST = ProtectedActionRequest(
    correlation_id=str(uuid.uuid4()),
    session_id="SES-00000042",
    agent_id="AGT-001",
    customer_scope="CUS-000123",
    task_type="account_inquiry",
    tool_name="get_customer",
    arguments={"customer_id": "CUS-000123"},
    provenance_labels={"customer_id": "system"},
    requested_at=RECEIVED,
)

CONTEXT = ActionContext(
    request=REQUEST,
    agent_id="AGT-001",
    agent=None,
    tool=None,
    session=None,
    session_error=None,
    received_at=RECEIVED,
)


def rule(name, stage, finding=NO_OBJECTION, *, log=None, error=None):
    """A check that records that it ran and returns ``finding`` (or raises ``error``)."""

    class Rule(Check):
        def evaluate(self, context, earlier):
            if log is not None:
                log.append((name, [record.check for record in earlier]))
            if error is not None:
                raise error
            return finding

    Rule.name = name
    Rule.stage = stage
    return Rule()


def block(reason=ReasonCode.POLICY_DENY, summary="Blocked by a bank rule."):
    return objection(Decision.BLOCK, reason, summary=summary)


def review(reason=ReasonCode.REFUND_OVER_LIMIT):
    return objection(
        Decision.HUMAN_REVIEW, reason, summary="A person must approve this."
    )


def quarantine():
    return objection(
        Decision.QUARANTINE,
        ReasonCode.REPEATED_VIOLATIONS,
        summary="The agent is contained.",
    )


def test_an_action_no_check_objects_to_is_allowed():
    verdict = Orchestrator([rule("a", Stage.CONTEXT), rule("b", Stage.RISK)]).decide(
        CONTEXT
    )

    assert verdict.decision is Decision.ALLOW
    assert verdict.reasons == (ReasonCode.WITHIN_POLICY,)
    assert verdict.summary == ALLOW_SUMMARY
    assert [record.check for record in verdict.records] == ["a", "b"]


def test_checks_run_in_stage_order_and_see_earlier_findings():
    log = []
    checks = [
        rule("risk", Stage.RISK, log=log),
        rule("containment", Stage.CONTAINMENT, log=log),
        rule("context", Stage.CONTEXT, log=log),
        rule("policy", Stage.HARD_RULE, log=log),
        rule("review", Stage.MANDATORY_REVIEW, log=log),
    ]

    Orchestrator(checks).decide(CONTEXT)

    assert log == [
        ("context", []),
        ("policy", ["context"]),
        ("containment", ["context", "policy"]),
        ("review", ["context", "policy", "containment"]),
        ("risk", ["context", "policy", "containment", "review"]),
    ]


def test_a_context_objection_stops_every_later_stage():
    log = []
    checks = [
        rule("session", Stage.CONTEXT, block(ReasonCode.MISSING_CONTEXT), log=log),
        rule("tool", Stage.CONTEXT, log=log),
        rule("policy", Stage.HARD_RULE, log=log),
    ]

    verdict = Orchestrator(checks).decide(CONTEXT)

    assert [name for name, _ in log] == ["session", "tool"]
    assert verdict.decision is Decision.BLOCK
    assert verdict.reasons == (ReasonCode.MISSING_CONTEXT,)


def test_review_and_risk_are_skipped_after_a_hard_stop():
    log = []
    checks = [
        rule("policy", Stage.HARD_RULE, block(), log=log),
        rule("containment", Stage.CONTAINMENT, log=log),
        rule("review", Stage.MANDATORY_REVIEW, review(), log=log),
        rule("risk", Stage.RISK, log=log),
    ]

    verdict = Orchestrator(checks).decide(CONTEXT)

    assert [name for name, _ in log] == ["policy", "containment"]
    assert verdict.decision is Decision.BLOCK


@pytest.mark.parametrize(
    ("findings", "expected", "reasons"),
    [
        pytest.param(
            [block(), quarantine()],
            Decision.QUARANTINE,
            (ReasonCode.REPEATED_VIOLATIONS, ReasonCode.POLICY_DENY),
            id="quarantine outranks block",
        ),
        pytest.param(
            [review(), block(ReasonCode.HIGH_RISK, "Too risky.")],
            Decision.BLOCK,
            (ReasonCode.HIGH_RISK, ReasonCode.REFUND_OVER_LIMIT),
            id="block outranks review",
        ),
        pytest.param(
            [review(), review(ReasonCode.HIGH_RISK)],
            Decision.HUMAN_REVIEW,
            (ReasonCode.REFUND_OVER_LIMIT, ReasonCode.HIGH_RISK),
            id="reviews combine",
        ),
        pytest.param(
            [block(), block()],
            Decision.BLOCK,
            (ReasonCode.POLICY_DENY,),
            id="reasons do not repeat",
        ),
    ],
)
def test_the_strongest_decision_wins_and_its_reasons_come_first(
    findings, expected, reasons
):
    records = [
        rule(f"check_{i}", Stage.HARD_RULE, finding)
        for i, finding in enumerate(findings)
    ]

    verdict = Orchestrator(records).decide(CONTEXT)

    assert verdict.decision is expected
    assert verdict.reasons == reasons


def test_the_summary_comes_from_the_first_finding_with_the_winning_decision():
    checks = [
        rule("a", Stage.HARD_RULE, review()),
        rule("b", Stage.HARD_RULE, block(summary="First block.")),
        rule("c", Stage.HARD_RULE, block(summary="Second block.")),
    ]

    assert Orchestrator(checks).decide(CONTEXT).summary == "First block."


def test_a_check_that_fails_blocks_the_action():
    checks = [
        rule("policy", Stage.HARD_RULE, error=TimeoutError("OPA did not answer")),
        rule("risk", Stage.RISK),
    ]

    verdict = Orchestrator(checks).decide(CONTEXT)

    assert verdict.decision is Decision.BLOCK
    assert verdict.reasons == (ReasonCode.DEPENDENCY_UNAVAILABLE,)
    assert "policy" in verdict.summary
    assert verdict.trace()[0]["details"] == {"error": "TimeoutError"}


def test_a_check_that_returns_the_wrong_type_blocks_the_action():
    verdict = Orchestrator([rule("broken", Stage.HARD_RULE, "ok")]).decide(CONTEXT)

    assert verdict.decision is Decision.BLOCK
    assert verdict.reasons == (ReasonCode.DEPENDENCY_UNAVAILABLE,)


def test_versions_are_reported_even_when_nothing_objects():
    checks = [
        rule("policy", Stage.HARD_RULE, Finding(policy_version="1.2.0")),
        rule("risk", Stage.RISK, Finding(model_version="0.3.1")),
    ]

    verdict = Orchestrator(checks).decide(CONTEXT)

    assert verdict.decision is Decision.ALLOW
    assert (verdict.policy_version, verdict.model_version) == ("1.2.0", "0.3.1")


def test_the_trace_lists_every_check_that_ran():
    checks = [
        rule("session", Stage.CONTEXT),
        rule(
            "policy",
            Stage.HARD_RULE,
            objection(
                Decision.BLOCK,
                ReasonCode.POLICY_DENY,
                summary="No.",
                rule="bulk_export",
            ),
        ),
    ]

    trace = Orchestrator(checks).decide(CONTEXT).trace()

    assert trace == [
        {
            "check": "session",
            "stage": "context",
            "decision": None,
            "reason_codes": [],
            "details": {},
        },
        {
            "check": "policy",
            "stage": "hard_rule",
            "decision": "BLOCK",
            "reason_codes": ["POLICY_DENY"],
            "details": {"rule": "bulk_export"},
        },
    ]


def test_an_orchestrator_needs_checks_with_unique_names():
    with pytest.raises(ValueError, match="at least one"):
        Orchestrator([])
    with pytest.raises(ValueError, match="unique"):
        Orchestrator([rule("a", Stage.CONTEXT), rule("a", Stage.RISK)])


def test_combining_no_findings_allows():
    assert combine([]).decision is Decision.ALLOW


@pytest.mark.parametrize(
    ("errors", "reasons", "fields"),
    [
        ([{"loc": ("session_id",)}], (ReasonCode.MISSING_CONTEXT,), ["session_id"]),
        ([{"loc": ("tool_name",)}], (ReasonCode.UNKNOWN_TOOL,), ["tool_name"]),
        (
            [{"loc": ("arguments", "amount")}],
            (ReasonCode.INVALID_ARGUMENTS,),
            ["arguments"],
        ),
        ([{"loc": ()}], (ReasonCode.INVALID_ARGUMENTS,), ["arguments"]),
        (
            [
                {"loc": ("provenance_labels",)},
                {"loc": ("tool_name",)},
                {"loc": ("agent_id",)},
            ],
            (
                ReasonCode.MISSING_CONTEXT,
                ReasonCode.UNKNOWN_TOOL,
                ReasonCode.INVALID_ARGUMENTS,
            ),
            ["agent_id", "provenance_labels", "tool_name"],
        ),
        ([], (ReasonCode.MISSING_CONTEXT,), []),
    ],
)
def test_validation_errors_become_a_block_with_matching_reasons(
    errors, reasons, fields
):
    verdict = invalid_request_verdict(errors)

    assert verdict.decision is Decision.BLOCK
    assert verdict.reasons == reasons
    assert verdict.trace()[0]["check"] == "request_shape"
    assert verdict.trace()[0]["details"] == {"fields": fields}


@pytest.mark.parametrize(
    "kwargs",
    [
        {
            "decision": Decision.ALLOW,
            "reasons": (ReasonCode.WITHIN_POLICY,),
            "summary": "Fine.",
        },
        {"decision": Decision.BLOCK},
        {"decision": Decision.BLOCK, "reasons": (ReasonCode.POLICY_DENY,)},
        {"reasons": (ReasonCode.POLICY_DENY,)},
    ],
)
def test_a_finding_must_be_a_complete_objection_or_none(kwargs):
    with pytest.raises(ValueError):
        Finding(**kwargs)
