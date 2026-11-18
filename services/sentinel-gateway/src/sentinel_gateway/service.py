"""What the gateway does with one action, from receipt to outcome (US-18.2 to US-18.5).

1. Bind the action to its context: the agent from its key, the customer session from
   the signed session token, never from what the request body claims.
2. Let the orchestrator decide.
3. Write action_received and decision_made to the audit trail. If either fails, stop
   with nothing executed.
4. For ALLOW, sign an execution token for exactly this call and forward it to the bank.
5. Write action_executed, approval_requested or action_stopped.
6. Keep the outcome under the correlation ID, so a repeat gets the same answer and
   the action runs at most once.
"""

import hashlib
import logging
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import JsonValue, TypeAdapter, ValidationError

from sentinel_contracts import (
    ActionOutcome,
    AuditEventType,
    AuditRecord,
    Decision,
    ExecutionError,
    ExecutionResult,
    ExecutionStatus,
    GovernanceDecision,
    ProtectedActionRequest,
    ReasonCode,
    SessionClaims,
    TokenError,
    issue_token,
    verify_session_token,
)
from sentinel_contracts.identifiers import ApprovalId, CorrelationId
from sentinel_contracts.signing import canonical_json
from sentinel_gateway.audit import AuditSink, AuditUnavailable
from sentinel_gateway.bank import BankClient
from sentinel_gateway.checks import ActionContext
from sentinel_gateway.config import Settings
from sentinel_gateway.decisions import DecisionStore
from sentinel_gateway.orchestrator import Orchestrator, Verdict, invalid_request_verdict
from sentinel_gateway.registry import AgentRegistry, ToolRegistry

ACTOR = "sentinel-gateway"
NO_APPROVALS_SUMMARY = (
    "The action needs a person's approval, but the approval service is not "
    "available, so it is blocked."
)

_CORRELATION_ID = TypeAdapter(CorrelationId)
_APPROVAL_ID = TypeAdapter(ApprovalId)
_FINAL_EVENT = {
    Decision.ALLOW: AuditEventType.ACTION_EXECUTED,
    Decision.HUMAN_REVIEW: AuditEventType.APPROVAL_REQUESTED,
    Decision.BLOCK: AuditEventType.ACTION_STOPPED,
    Decision.QUARANTINE: AuditEventType.ACTION_STOPPED,
}

log = logging.getLogger("sentinel_gateway")


class ApprovalRequester(Protocol):
    """Opens an approval request for a held action. Built in US-03."""

    def request_approval(
        self, request: ProtectedActionRequest, verdict: Verdict
    ) -> str:
        """Create the request and return its ID, such as APR-000007."""
        ...


@dataclass(frozen=True)
class Evaluation:
    """An outcome, and whether it was stored from an earlier identical request."""

    outcome: ActionOutcome
    replayed: bool

    @property
    def correlation_id(self) -> str:
        return self.outcome.decision.correlation_id


class Gateway:
    def __init__(
        self,
        *,
        settings: Settings,
        agents: AgentRegistry,
        tools: ToolRegistry,
        orchestrator: Orchestrator,
        decisions: DecisionStore,
        bank: BankClient,
        audit: AuditSink,
        approvals: ApprovalRequester | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._settings = settings
        self._agents = agents
        self._tools = tools
        self._orchestrator = orchestrator
        self._decisions = decisions
        self._bank = bank
        self._audit = audit
        self._approvals = approvals
        self._clock = clock

    def evaluate(
        self,
        body: Mapping[str, Any],
        *,
        agent_id: str,
        session_token: str | None,
    ) -> Evaluation:
        """Decide on one action and, if it is allowed, run it.

        ``agent_id`` is the authenticated caller. A request without a valid correlation
        ID is given a new one and blocked, so it is still decided and audited.
        """
        correlation_id = _correlation_id(body.get("correlation_id"))
        if correlation_id is None:
            fresh_id = str(uuid.uuid4())
            outcome = self._process(fresh_id, body, agent_id, session_token)
            return Evaluation(outcome, replayed=False)

        outcome, replayed = self._decisions.run_once(
            correlation_id,
            _fingerprint(agent_id, session_token, body),
            lambda: self._process(correlation_id, body, agent_id, session_token),
        )
        if replayed:
            log.info("repeat of %s answered from the stored outcome", correlation_id)
        return Evaluation(outcome, replayed=replayed)

    def _process(
        self,
        correlation_id: str,
        body: Mapping[str, Any],
        agent_id: str,
        session_token: str | None,
    ) -> ActionOutcome:
        received_at = self._now()
        session, session_error = self._verify_session(session_token)
        request: ProtectedActionRequest | None = None
        try:
            request = ProtectedActionRequest.model_validate(body)
        except ValidationError as exc:
            verdict = invalid_request_verdict(
                exc.errors(
                    include_url=False, include_context=False, include_input=False
                )
            )

        self._write(
            AuditEventType.ACTION_RECEIVED,
            correlation_id,
            payload={
                "authenticated_agent_id": agent_id,
                "session": session.model_dump(mode="json") if session else None,
                "session_error": session_error,
                "request": dict(body),
            },
        )

        if request is not None:
            verdict = self._orchestrator.decide(
                ActionContext(
                    request=request,
                    agent_id=agent_id,
                    agent=self._agents.get(agent_id),
                    tool=self._tools.get(request.tool_name),
                    session=session,
                    session_error=session_error,
                    received_at=received_at,
                )
            )
        decision = self._decision(correlation_id, request, verdict)
        self._write(
            AuditEventType.DECISION_MADE,
            correlation_id,
            decision=decision.decision,
            policy_version=decision.policy_version,
            model_version=decision.model_version,
            payload={
                "reason_codes": [reason.value for reason in decision.reason_codes],
                "summary": decision.summary,
                "approval_id": decision.approval_id,
                "checks": verdict.trace(),
            },
        )

        execution = None
        if request is not None and decision.permits_execution:
            execution = self._execute(request, decision)
        outcome = ActionOutcome(decision=decision, execution=execution)
        self._write_final(outcome)
        log.info(
            "%s %s for %s (agent %s): %s",
            decision.decision.value,
            request.tool_name if request is not None else "an invalid request",
            correlation_id,
            agent_id,
            ", ".join(reason.value for reason in decision.reason_codes),
        )
        return outcome

    def _execute(
        self, request: ProtectedActionRequest, decision: GovernanceDecision
    ) -> ExecutionResult:
        try:
            return self._bank.execute(
                request.tool_name, request.arguments, decision.execution_token
            )
        except Exception:
            # The outcome must still be stored, or a retry could run the action twice.
            log.exception("forwarding %s failed", request.correlation_id)
            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                tool_name=request.tool_name,
                error=ExecutionError(
                    code="gateway_error",
                    message="the gateway could not complete the call to the bank",
                ),
                completed_at=self._now(),
            )

    def _decision(
        self,
        correlation_id: str,
        request: ProtectedActionRequest | None,
        verdict: Verdict,
    ) -> GovernanceDecision:
        decision = verdict.decision
        reasons = list(verdict.reasons)
        summary = verdict.summary
        approval_id = None
        token = None
        if decision is Decision.HUMAN_REVIEW and request is not None:
            approval_id = self._open_approval(request, verdict)
            if approval_id is None:
                decision = Decision.BLOCK
                reasons.insert(0, ReasonCode.DEPENDENCY_UNAVAILABLE)
                summary = NO_APPROVALS_SUMMARY
        if decision is Decision.ALLOW and request is not None:
            token = issue_token(
                key=self._settings.execution_token_key,
                correlation_id=correlation_id,
                tool_name=request.tool_name,
                arguments=request.arguments,
                customer_scope=request.customer_scope,
                audience=self._settings.bank_audience,
                now=self._clock(),
            )
        return GovernanceDecision(
            correlation_id=correlation_id,
            decision=decision,
            reason_codes=list(dict.fromkeys(reasons)),
            summary=summary,
            policy_version=verdict.policy_version,
            model_version=verdict.model_version,
            approval_id=approval_id,
            execution_token=token,
            decided_at=self._now(),
        )

    def _open_approval(
        self, request: ProtectedActionRequest, verdict: Verdict
    ) -> str | None:
        if self._approvals is None:
            return None
        try:
            return _APPROVAL_ID.validate_python(
                self._approvals.request_approval(request, verdict)
            )
        except Exception:
            log.exception("could not open an approval for %s", request.correlation_id)
            return None

    def _verify_session(
        self, token: str | None
    ) -> tuple[SessionClaims | None, str | None]:
        if not token:
            return None, None
        try:
            claims = verify_session_token(
                token, key=self._settings.session_token_key, now=self._clock()
            )
        except TokenError as exc:
            return None, exc.code
        return claims, None

    def _write_final(self, outcome: ActionOutcome) -> None:
        decision = outcome.decision
        payload: dict[str, JsonValue] = {
            "reason_codes": [reason.value for reason in decision.reason_codes]
        }
        if outcome.execution is not None:
            payload = outcome.execution.model_dump(
                mode="json", include={"tool_name", "status", "http_status", "error"}
            )
        if decision.approval_id is not None:
            payload["approval_id"] = decision.approval_id
        try:
            self._write(
                _FINAL_EVENT[decision.decision],
                decision.correlation_id,
                decision=decision.decision,
                payload=payload,
            )
        except AuditUnavailable:
            # The action has already run or been stopped; the outcome must still be
            # returned and kept, so the gap is logged for the operator instead.
            log.exception("final audit record lost for %s", decision.correlation_id)

    def _write(
        self,
        event_type: AuditEventType,
        correlation_id: str,
        *,
        payload: dict[str, JsonValue],
        decision: Decision | None = None,
        policy_version: str | None = None,
        model_version: str | None = None,
    ) -> None:
        try:
            self._audit.record(
                AuditRecord(
                    correlation_id=correlation_id,
                    event_type=event_type,
                    actor=ACTOR,
                    decision=decision,
                    policy_version=policy_version,
                    model_version=model_version,
                    payload=payload,
                    created_at=self._now(),
                )
            )
        except Exception as exc:
            raise AuditUnavailable(f"could not write {event_type.value}") from exc

    def _now(self) -> datetime:
        return datetime.fromtimestamp(self._clock(), tz=UTC)


def _correlation_id(value: Any) -> str | None:
    try:
        return _CORRELATION_ID.validate_python(value)
    except ValidationError:
        return None


def _fingerprint(
    agent_id: str, session_token: str | None, body: Mapping[str, Any]
) -> str:
    """Identify a request by its caller, its session and its exact content."""
    session = (
        hashlib.sha256(session_token.encode()).hexdigest() if session_token else None
    )
    material = {"agent_id": agent_id, "session": session, "request": dict(body)}
    return hashlib.sha256(canonical_json(material)).hexdigest()
