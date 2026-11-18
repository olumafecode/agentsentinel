"""Audit completeness: does every action have its whole story? (US-19.5, NFR-06)

A complete trail for one correlation ID has, in this order:

1. at least one ``action_received`` (a retry after an audit failure may add a second);
2. exactly one ``decision_made`` with a decision and at least one reason code;
3. exactly one final event that fits the decision: ``action_executed`` for ALLOW,
   ``approval_requested`` for HUMAN_REVIEW, ``action_stopped`` for BLOCK and
   QUARANTINE.

The check works on stored events and on the gateway's AuditRecords alike, so the
scenario evaluation in US-26 can reuse it. US-03 extends the rule for approvals.
"""

from collections.abc import Collection, Iterable
from dataclasses import dataclass
from typing import Any, Protocol

RECEIVED = "action_received"
DECIDED = "decision_made"
FINAL_EVENT = {
    "ALLOW": "action_executed",
    "HUMAN_REVIEW": "approval_requested",
    "BLOCK": "action_stopped",
    "QUARANTINE": "action_stopped",
}


class AuditedEvent(Protocol):
    correlation_id: str
    event_type: Any
    decision: Any
    payload: Any


@dataclass(frozen=True)
class IncompleteTrail:
    correlation_id: str
    problems: tuple[str, ...]


@dataclass(frozen=True)
class CompletenessReport:
    actions: int
    incomplete: tuple[IncompleteTrail, ...]

    @property
    def complete(self) -> int:
        return self.actions - len(self.incomplete)

    @property
    def ratio(self) -> float:
        """Share of actions with a complete trail; 1.0 when there are none."""
        return self.complete / self.actions if self.actions else 1.0

    @property
    def ok(self) -> bool:
        return not self.incomplete


def check_completeness(
    events: Iterable[AuditedEvent], *, expected: Collection[str] = ()
) -> CompletenessReport:
    """Check every correlation ID in ``events``, in the order they were written.

    ``expected`` lists correlation IDs that must be present, for example the actions
    a scenario run proposed; one with no events at all is reported as incomplete.
    """
    trails: dict[str, list[AuditedEvent]] = {cid: [] for cid in expected}
    for event in events:
        trails.setdefault(str(event.correlation_id), []).append(event)
    incomplete = []
    for correlation_id, trail in trails.items():
        problems = _problems(trail)
        if problems:
            incomplete.append(IncompleteTrail(correlation_id, tuple(problems)))
    return CompletenessReport(actions=len(trails), incomplete=tuple(incomplete))


def _problems(trail: list[AuditedEvent]) -> list[str]:
    if not trail:
        return ["no audit events at all"]
    kinds = [_value(event.event_type) for event in trail]
    problems = []
    if RECEIVED not in kinds:
        problems.append("action_received is missing")
    decisions = [event for event in trail if _value(event.event_type) == DECIDED]
    if len(decisions) != 1:
        problems.append(f"expected one decision_made, found {len(decisions)}")
        return problems

    decided = decisions[0]
    decision = _value(decided.decision)
    reasons = (decided.payload or {}).get("reason_codes")
    if decision not in FINAL_EVENT:
        problems.append("decision_made has no decision")
        return problems
    if not reasons:
        problems.append("decision_made has no reason codes")
    if RECEIVED in kinds and kinds.index(RECEIVED) > kinds.index(DECIDED):
        problems.append("decision_made comes before action_received")

    final = FINAL_EVENT[decision]
    after = kinds[kinds.index(DECIDED) + 1 :]
    finals = [kind for kind in kinds if kind in FINAL_EVENT.values()]
    if after.count(final) != 1 or len(finals) != 1:
        problems.append(f"expected one {final} after the {decision} decision")
    return problems


def _value(value: Any) -> Any:
    return getattr(value, "value", value)
