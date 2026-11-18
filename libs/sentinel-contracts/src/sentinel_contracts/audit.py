"""Audit records the gateway writes for every evaluated action (FR-13, NFR-06).

An AuditRecord is an AuditEvent from data/synthetic/models.py before the audit service
stores it: the audit service (US-19) adds the event ID and the hash chain. The event
types are the same as AuditEventType in the schema.
"""

from enum import StrEnum
from typing import Annotated

from pydantic import AwareDatetime, Field, JsonValue, StringConstraints

from sentinel_contracts.actions import Contract, Decision
from sentinel_contracts.identifiers import CorrelationId, SemVer


class AuditEventType(StrEnum):
    ACTION_RECEIVED = "action_received"
    POLICY_EVALUATED = "policy_evaluated"
    RISK_ASSESSED = "risk_assessed"
    DECISION_MADE = "decision_made"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_DECIDED = "approval_decided"
    ACTION_EXECUTED = "action_executed"
    ACTION_STOPPED = "action_stopped"
    AGENT_QUARANTINED = "agent_quarantined"
    EXPLANATION_GENERATED = "explanation_generated"


class AuditRecord(Contract):
    """One step in the life of an action, ready to be added to the audit chain."""

    correlation_id: CorrelationId = Field(description="Action the event describes")
    event_type: AuditEventType = Field(description="What happened")
    actor: Annotated[str, StringConstraints(min_length=3, max_length=40)] = Field(
        description="Service, agent or staff member that acted"
    )
    decision: Decision | None = Field(
        default=None, description="Outcome, on decision events"
    )
    policy_version: SemVer | None = Field(
        default=None, description="Policy bundle in force"
    )
    model_version: SemVer | None = Field(
        default=None, description="Risk model in force"
    )
    payload: dict[str, JsonValue] = Field(
        description="Decision inputs and results for this step"
    )
    created_at: AwareDatetime = Field(description="When the event happened")
