"""Turns the checks' findings into one decision (US-18.3, ADR-012).

Deny by default: an action is allowed only when every check ran and none objected.
When checks disagree, the strongest decision wins, in the precedence order of
proposal Appendix E as agreed for this project: QUARANTINE, then BLOCK, then
HUMAN_REVIEW, then ALLOW. Two shortcuts keep the path fast and safe:

- If a CONTEXT check objects, nothing else runs. Without a trusted context the other
  rules have nothing reliable to judge.
- Once any check has asked for BLOCK or QUARANTINE, the review and risk stages are
  skipped, because neither can overturn a hard stop (ADR-003).

A check that raises an exception counts as a BLOCK with DEPENDENCY_UNAVAILABLE, so a
broken rule or an unreachable policy engine fails closed.
"""

import logging
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sentinel_contracts import Decision, ReasonCode
from sentinel_gateway.checks import (
    ActionContext,
    Check,
    CheckRecord,
    Finding,
    Stage,
    objection,
)

ALLOW_SUMMARY = "The action passed every check and is allowed."
INVALID_REQUEST_SUMMARY = (
    "The action request is incomplete or malformed, so it is blocked."
)

_RANK = {Decision.HUMAN_REVIEW: 1, Decision.BLOCK: 2, Decision.QUARANTINE: 3}
_HARD_STOPS = (Decision.BLOCK, Decision.QUARANTINE)
_ARGUMENT_FIELDS = frozenset({"arguments", "provenance_labels"})
_SHAPE_REASON_ORDER = (
    ReasonCode.MISSING_CONTEXT,
    ReasonCode.UNKNOWN_TOOL,
    ReasonCode.INVALID_ARGUMENTS,
)

log = logging.getLogger("sentinel_gateway.orchestrator")


@dataclass(frozen=True)
class Verdict:
    """The orchestrator's decision and the findings that led to it."""

    decision: Decision
    reasons: tuple[ReasonCode, ...]
    summary: str
    policy_version: str | None
    model_version: str | None
    records: tuple[CheckRecord, ...]

    def trace(self) -> list[dict[str, Any]]:
        """Each check's result, in the order it ran, for the audit record."""
        return [
            {
                "check": record.check,
                "stage": record.stage.name.lower(),
                "decision": (
                    record.finding.decision.value if record.finding.objects else None
                ),
                "reason_codes": [reason.value for reason in record.finding.reasons],
                "details": dict(record.finding.details),
            }
            for record in self.records
        ]


class Orchestrator:
    """Runs the checks for one action and combines their findings."""

    def __init__(self, checks: Iterable[Check]) -> None:
        ordered = sorted(checks, key=lambda check: check.stage)
        if not ordered:
            raise ValueError("the orchestrator needs at least one check")
        names = [check.name for check in ordered]
        if len(set(names)) != len(names):
            raise ValueError(f"check names must be unique: {names}")
        self._checks = tuple(ordered)

    @property
    def checks(self) -> tuple[Check, ...]:
        return self._checks

    def decide(self, context: ActionContext) -> Verdict:
        records: list[CheckRecord] = []
        for check in self._checks:
            if _must_stop_before(check.stage, records):
                break
            records.append(
                CheckRecord(check.name, check.stage, _run(check, context, records))
            )
        return combine(records)


def combine(records: Sequence[CheckRecord]) -> Verdict:
    """Apply the precedence order to a set of findings."""
    policy_version = next(
        (r.finding.policy_version for r in records if r.finding.policy_version), None
    )
    model_version = next(
        (r.finding.model_version for r in records if r.finding.model_version), None
    )
    objections = [r for r in records if r.finding.objects]
    if not objections:
        return Verdict(
            decision=Decision.ALLOW,
            reasons=(ReasonCode.WITHIN_POLICY,),
            summary=ALLOW_SUMMARY,
            policy_version=policy_version,
            model_version=model_version,
            records=tuple(records),
        )
    decision = max((r.finding.decision for r in objections), key=_RANK.__getitem__)
    leading = [r for r in objections if r.finding.decision is decision]
    others = [r for r in objections if r.finding.decision is not decision]
    reasons = dict.fromkeys(
        reason for record in leading + others for reason in record.finding.reasons
    )
    return Verdict(
        decision=decision,
        reasons=tuple(reasons),
        summary=leading[0].finding.summary,
        policy_version=policy_version,
        model_version=model_version,
        records=tuple(records),
    )


def invalid_request_verdict(errors: Sequence[Mapping[str, Any]]) -> Verdict:
    """BLOCK an action whose request failed validation, with reasons for each problem.

    Problems with the tool name give UNKNOWN_TOOL, problems with the arguments or their
    provenance labels give INVALID_ARGUMENTS, and anything else is MISSING_CONTEXT.
    """
    found: set[ReasonCode] = set()
    fields: set[str] = set()
    for error in errors:
        location = tuple(str(part) for part in error.get("loc", ()))
        field = location[0] if location else "arguments"
        fields.add(field)
        if field == "tool_name":
            found.add(ReasonCode.UNKNOWN_TOOL)
        elif field in _ARGUMENT_FIELDS:
            found.add(ReasonCode.INVALID_ARGUMENTS)
        else:
            found.add(ReasonCode.MISSING_CONTEXT)
    reasons = [r for r in _SHAPE_REASON_ORDER if r in found] or [
        ReasonCode.MISSING_CONTEXT
    ]
    finding = objection(
        Decision.BLOCK,
        *reasons,
        summary=INVALID_REQUEST_SUMMARY,
        fields=sorted(fields),
    )
    return combine([CheckRecord("request_shape", Stage.CONTEXT, finding)])


def _must_stop_before(stage: Stage, records: Sequence[CheckRecord]) -> bool:
    if stage > Stage.CONTEXT and any(
        r.stage is Stage.CONTEXT and r.finding.objects for r in records
    ):
        return True
    return stage >= Stage.MANDATORY_REVIEW and any(
        r.finding.decision in _HARD_STOPS for r in records
    )


def _run(
    check: Check, context: ActionContext, earlier: Sequence[CheckRecord]
) -> Finding:
    try:
        finding = check.evaluate(context, tuple(earlier))
        if not isinstance(finding, Finding):
            raise TypeError(
                f"{check.name} returned {type(finding).__name__}, not a Finding"
            )
    except Exception as exc:
        log.exception(
            "check %s failed for correlation %s",
            check.name,
            context.request.correlation_id,
        )
        return objection(
            Decision.BLOCK,
            ReasonCode.DEPENDENCY_UNAVAILABLE,
            summary=f"The {check.name} check could not run, so the action is blocked.",
            error=type(exc).__name__,
        )
    return finding
