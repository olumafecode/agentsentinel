"""Audit completeness: every action has its whole story (US-19.5)."""

import uuid
from dataclasses import dataclass

import pytest

from sentinel_audit.completeness import check_completeness


@dataclass
class Event:
    correlation_id: str
    event_type: str
    decision: str | None = None
    payload: dict | None = None


def trail(decision="ALLOW", *, final=None, cid=None):
    cid = cid or str(uuid.uuid4())
    final = (
        final
        or {
            "ALLOW": "action_executed",
            "HUMAN_REVIEW": "approval_requested",
            "BLOCK": "action_stopped",
            "QUARANTINE": "action_stopped",
        }[decision]
    )
    return [
        Event(cid, "action_received"),
        Event(cid, "decision_made", decision, {"reason_codes": ["WITHIN_POLICY"]}),
        Event(cid, final, decision, {}),
    ]


@pytest.mark.parametrize("decision", ["ALLOW", "HUMAN_REVIEW", "BLOCK", "QUARANTINE"])
def test_a_full_trail_is_complete(decision):
    report = check_completeness(trail(decision))

    assert report.ok
    assert (report.actions, report.complete, report.ratio) == (1, 1, 1.0)


def test_a_retry_after_an_audit_failure_may_repeat_action_received():
    events = trail()
    events.insert(1, events[0])

    assert check_completeness(events).ok


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        (lambda t: t[1:], "action_received is missing"),
        (lambda t: [t[0], t[2]], "expected one decision_made, found 0"),
        (lambda t: [t[0], t[1], t[1], t[2]], "expected one decision_made, found 2"),
        (lambda t: t[:2], "expected one action_executed after the ALLOW decision"),
        (lambda t: [*t, t[2]], "expected one action_executed after the ALLOW decision"),
        (lambda t: [t[1], t[0], t[2]], "decision_made comes before action_received"),
        (
            lambda t: [
                t[0],
                Event(t[1].correlation_id, "decision_made", "ALLOW", {}),
                t[2],
            ],
            "decision_made has no reason codes",
        ),
        (
            lambda t: [
                t[0],
                Event(t[1].correlation_id, "decision_made", None, {}),
                t[2],
            ],
            "decision_made has no decision",
        ),
    ],
)
def test_a_gap_in_the_trail_is_reported(change, problem):
    report = check_completeness(change(trail()))

    assert not report.ok
    assert problem in report.incomplete[0].problems


def test_a_final_event_that_does_not_fit_the_decision_is_reported():
    report = check_completeness(trail("BLOCK", final="action_executed"))

    assert report.incomplete[0].problems == (
        "expected one action_stopped after the BLOCK decision",
    )


def test_an_expected_action_without_any_events_is_reported():
    missing = str(uuid.uuid4())

    report = check_completeness(trail(), expected=[missing])

    assert report.actions == 2
    assert report.ratio == 0.5
    assert report.incomplete[0].correlation_id == missing
    assert report.incomplete[0].problems == ("no audit events at all",)


def test_no_actions_counts_as_complete():
    report = check_completeness([])

    assert report.ok
    assert report.ratio == 1.0
