"""The checks every action passes through before the gateway decides (US-18.3, ADR-012).

A check looks at one action and returns a Finding: either no objection, or the
decision it asks for with reason codes and a one-line summary. Checks never allow an
action; an action is allowed only when no check objects. Each check belongs to a
stage, and the orchestrator runs the stages in order:

CONTEXT           Who is asking, for which customer session, with which tool.
HARD_RULE         Deterministic bank rules (US-01 scope and allowlist, US-02 OPA).
CONTAINMENT       Whether the agent must be contained (US-05 quarantine).
MANDATORY_REVIEW  Actions that always need a person (US-03 large refunds).
RISK              The machine learning risk signal (US-04), advisory only (ADR-003).

To add a rule, subclass Check, set its name and stage, and add it to default_checks.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import IntEnum
from typing import Any, ClassVar

from sentinel_contracts import (
    Decision,
    ProtectedActionRequest,
    ReasonCode,
    SessionClaims,
)
from sentinel_gateway.registry import AgentProfile, AgentStatus, ToolProfile

MAX_REQUEST_AGE = timedelta(minutes=5)
"""Requests older than this are refused, so an old request can never run again."""
MAX_CLOCK_AHEAD = timedelta(seconds=30)
"""How far an agent's clock may run ahead of the gateway's."""

_ABSENT_OR_LAPSED = (None, "session_expired", "session_not_yet_valid")
"""Session problems that mean missing context. Any other one suggests tampering."""


class Stage(IntEnum):
    """Evaluation order. Lower stages run first."""

    CONTEXT = 1
    HARD_RULE = 2
    CONTAINMENT = 3
    MANDATORY_REVIEW = 4
    RISK = 5


@dataclass(frozen=True)
class Finding:
    """What one check concluded about one action.

    ``decision`` is None when the check has no objection. A check that has one asks
    for HUMAN_REVIEW, BLOCK or QUARANTINE and gives at least one reason and a summary.
    A check that consults a versioned policy or model reports the version even when
    it has no objection, so an ALLOW decision records what it was judged against.
    """

    decision: Decision | None = None
    reasons: tuple[ReasonCode, ...] = ()
    summary: str = ""
    policy_version: str | None = None
    model_version: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.decision is Decision.ALLOW:
            raise ValueError("a check cannot allow an action, only object to it")
        if self.decision is not None and not (self.reasons and self.summary):
            raise ValueError("an objection needs at least one reason and a summary")
        if self.decision is None and self.reasons:
            raise ValueError("reasons are only given with an objection")

    @property
    def objects(self) -> bool:
        return self.decision is not None


NO_OBJECTION = Finding()


def objection(
    decision: Decision, *reasons: ReasonCode, summary: str, **details: Any
) -> Finding:
    """Shorthand for a finding that asks for ``decision``."""
    return Finding(decision=decision, reasons=reasons, summary=summary, details=details)


@dataclass(frozen=True)
class CheckRecord:
    """A finding together with the check and stage that produced it."""

    check: str
    stage: Stage
    finding: Finding


@dataclass(frozen=True)
class ActionContext:
    """Everything the checks may look at for one action.

    The agent ID comes from the agent's credential and the session from a verified
    session token, never from the request body.
    """

    request: ProtectedActionRequest
    agent_id: str
    agent: AgentProfile | None
    tool: ToolProfile | None
    session: SessionClaims | None
    session_error: str | None
    received_at: datetime


class Check(ABC):
    """One rule. Subclasses set ``name`` and ``stage`` and implement ``evaluate``."""

    name: ClassVar[str]
    stage: ClassVar[Stage]

    @abstractmethod
    def evaluate(
        self, context: ActionContext, earlier: Sequence[CheckRecord]
    ) -> Finding:
        """Judge the action. ``earlier`` holds the findings of the checks that ran before."""


class ContextBindingCheck(Check):
    """The action must belong to the calling agent and to a valid customer session (FR-02).

    The agent ID, session, customer and task in the request must all match the agent's
    credential and the signed session token. Any difference means the agent is
    claiming a context it does not have.
    """

    name = "context_binding"
    stage = Stage.CONTEXT

    def evaluate(
        self, context: ActionContext, earlier: Sequence[CheckRecord]
    ) -> Finding:
        request = context.request
        if request.agent_id != context.agent_id:
            return objection(
                Decision.BLOCK,
                ReasonCode.IDENTITY_MISMATCH,
                summary="The action names a different agent from the one that sent it.",
                field="agent_id",
            )
        session = context.session
        if session is None:
            missing = context.session_error in _ABSENT_OR_LAPSED
            return objection(
                Decision.BLOCK,
                ReasonCode.MISSING_CONTEXT if missing else ReasonCode.IDENTITY_MISMATCH,
                summary="The action has no valid customer session, so it cannot be "
                "tied to a signed-in customer.",
                session_error=context.session_error or "session_missing",
            )
        expected = {
            "agent_id": session.agent_id,
            "session_id": session.session_id,
            "customer_scope": session.customer_id,
            "task_type": session.task_type,
        }
        mismatched = sorted(
            name for name, value in expected.items() if getattr(request, name) != value
        )
        if mismatched:
            return objection(
                Decision.BLOCK,
                ReasonCode.IDENTITY_MISMATCH,
                summary="The action does not match the customer session it claims "
                f"to belong to ({', '.join(mismatched)}).",
                fields=mismatched,
            )
        return NO_OBJECTION


class AgentStatusCheck(Check):
    """Only registered, active agents may act. A quarantined agent stays contained."""

    name = "agent_status"
    stage = Stage.CONTEXT

    def evaluate(
        self, context: ActionContext, earlier: Sequence[CheckRecord]
    ) -> Finding:
        agent = context.agent
        if agent is None:
            return objection(
                Decision.BLOCK,
                ReasonCode.IDENTITY_MISMATCH,
                summary="The agent is not registered with the gateway.",
            )
        if agent.status is AgentStatus.QUARANTINED:
            return objection(
                Decision.QUARANTINE,
                ReasonCode.AGENT_QUARANTINED,
                summary=f"{agent.name} is quarantined, so none of its actions can run "
                "until an administrator releases it.",
            )
        if agent.status is AgentStatus.DISABLED:
            return objection(
                Decision.BLOCK,
                ReasonCode.AGENT_DISABLED,
                summary=f"{agent.name} is disabled, so none of its actions can run.",
            )
        return NO_OBJECTION


class RequestFreshnessCheck(Check):
    """The action must have been proposed just now, not replayed from the past."""

    name = "request_freshness"
    stage = Stage.CONTEXT

    def evaluate(
        self, context: ActionContext, earlier: Sequence[CheckRecord]
    ) -> Finding:
        age = context.received_at - context.request.requested_at
        if age > MAX_REQUEST_AGE or -age > MAX_CLOCK_AHEAD:
            minutes = int(MAX_REQUEST_AGE.total_seconds() // 60)
            return objection(
                Decision.BLOCK,
                ReasonCode.STALE_REQUEST,
                summary=f"The action was proposed more than {minutes} minutes ago or "
                "carries a time in the future, so it is refused.",
                age_seconds=round(age.total_seconds(), 3),
            )
        return NO_OBJECTION


class KnownToolCheck(Check):
    """Only tools in the gateway's registry may be called (deny by default, NFR-01)."""

    name = "known_tool"
    stage = Stage.CONTEXT

    def evaluate(
        self, context: ActionContext, earlier: Sequence[CheckRecord]
    ) -> Finding:
        if context.tool is None:
            return objection(
                Decision.BLOCK,
                ReasonCode.UNKNOWN_TOOL,
                summary=f"There is no known tool called {context.request.tool_name}.",
            )
        return NO_OBJECTION


def default_checks() -> list[Check]:
    """The checks the gateway runs, in the order they appear within each stage."""
    return [
        ContextBindingCheck(),
        AgentStatusCheck(),
        RequestFreshnessCheck(),
        KnownToolCheck(),
    ]
