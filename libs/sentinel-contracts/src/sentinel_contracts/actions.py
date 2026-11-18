"""Request and decision contracts between Vera and the Sentinel Gateway (US-18.1).

Field names and formats follow proposal Appendix E and the ToolCall entity in
data/synthetic/models.py, so a stored ToolCall and a live ProtectedActionRequest
have the same shape.
"""

from enum import StrEnum
from typing import Annotated, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    model_validator,
)

from sentinel_contracts.identifiers import (
    AgentId,
    ApprovalId,
    ArgumentName,
    CorrelationId,
    CustomerId,
    SemVer,
    SessionId,
    ToolName,
)

MAX_ARGUMENTS = 32
"""Upper bound on arguments in one tool call; real bank tools take far fewer."""


class Decision(StrEnum):
    """The single outcome every evaluated action ends in (FR-08)."""

    ALLOW = "ALLOW"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    BLOCK = "BLOCK"
    QUARANTINE = "QUARANTINE"


class Provenance(StrEnum):
    """Where an argument value came from (FR-05)."""

    TRUSTED_USER_INPUT = "trusted_user_input"
    UNTRUSTED_CONTENT = "untrusted_content"
    SYSTEM = "system"


class TaskType(StrEnum):
    """What the customer asked the agent to do."""

    ACCOUNT_INQUIRY = "account_inquiry"
    REFUND_REQUEST = "refund_request"
    PROFILE_UPDATE = "profile_update"
    DISPUTE = "dispute"
    ADMIN_MAINTENANCE = "admin_maintenance"


class ReasonCode(StrEnum):
    """Machine-readable reasons for a decision. Add a member when a new rule needs one."""

    WITHIN_POLICY = "WITHIN_POLICY"
    MISSING_CONTEXT = "MISSING_CONTEXT"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    UNKNOWN_TOOL = "UNKNOWN_TOOL"
    TOOL_NOT_ALLOWED = "TOOL_NOT_ALLOWED"
    OUTSIDE_CUSTOMER_SCOPE = "OUTSIDE_CUSTOMER_SCOPE"
    INVALID_ARGUMENTS = "INVALID_ARGUMENTS"
    POLICY_DENY = "POLICY_DENY"
    UNTRUSTED_ORIGIN = "UNTRUSTED_ORIGIN"
    REFUND_OVER_LIMIT = "REFUND_OVER_LIMIT"
    HIGH_RISK = "HIGH_RISK"
    REPEATED_VIOLATIONS = "REPEATED_VIOLATIONS"
    AGENT_QUARANTINED = "AGENT_QUARANTINED"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
    APPROVED_BY_HUMAN = "APPROVED_BY_HUMAN"
    REJECTED_BY_HUMAN = "REJECTED_BY_HUMAN"


Summary = Annotated[str, StringConstraints(min_length=3, max_length=300)]


class Contract(BaseModel):
    """Base for every contract: unknown fields are rejected and values cannot change."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ProtectedActionRequest(Contract):
    """One action the agent proposes. Nothing reaches a bank tool until it is evaluated.

    The gateway does not take agent_id, session_id or customer_scope on trust. It
    compares them with the caller's credentials and session (US-18.2) and denies the
    action when they disagree.
    """

    correlation_id: CorrelationId = Field(
        description="UUID version 4 that ties every record of this action together"
    )
    session_id: SessionId = Field(description="Session the action belongs to")
    agent_id: AgentId = Field(description="Agent proposing the action")
    customer_scope: CustomerId = Field(description="Customer the session is bound to")
    task_type: TaskType = Field(description="Task the agent is working on")
    tool_name: ToolName = Field(description="Tool the agent wants to call")
    arguments: dict[ArgumentName, JsonValue] = Field(
        max_length=MAX_ARGUMENTS,
        description="Tool arguments as JSON values; send money amounts as strings",
    )
    provenance_labels: dict[ArgumentName, Provenance] = Field(
        description="Origin of each argument; a sensitive argument without a label "
        "is treated as untrusted"
    )
    requested_at: AwareDatetime = Field(
        description="When the agent proposed the action"
    )

    @model_validator(mode="after")
    def _labels_refer_to_arguments(self) -> Self:
        unknown = sorted(set(self.provenance_labels) - set(self.arguments))
        if unknown:
            raise ValueError(
                f"provenance labels for arguments that do not exist: {unknown}"
            )
        return self


class GovernanceDecision(Contract):
    """The gateway's answer to one ProtectedActionRequest (FR-08).

    ALLOW always carries a signed single-use execution token, and no other outcome
    may carry one. HUMAN_REVIEW always carries the approval request ID; ALLOW or
    BLOCK may also carry it when they follow a person's approval or rejection.
    """

    correlation_id: CorrelationId = Field(description="Action this decision answers")
    decision: Decision = Field(description="ALLOW, HUMAN_REVIEW, BLOCK or QUARANTINE")
    reason_codes: list[ReasonCode] = Field(
        min_length=1, description="Why the decision was made, most important first"
    )
    summary: Summary = Field(
        description="One plain-English sentence the agent can relay"
    )
    policy_version: SemVer | None = Field(
        default=None, description="Policy bundle in force, once OPA is in place"
    )
    model_version: SemVer | None = Field(
        default=None, description="Risk model in force, when the action was scored"
    )
    approval_id: ApprovalId | None = Field(
        default=None, description="Approval request, for HUMAN_REVIEW and its outcome"
    )
    execution_token: str | None = Field(
        default=None,
        min_length=1,
        max_length=4096,
        description="Signed single-use token, present only when the decision is ALLOW",
    )
    decided_at: AwareDatetime = Field(description="When the decision was made")

    @model_validator(mode="after")
    def _outcome_fields_match_decision(self) -> Self:
        if len(set(self.reason_codes)) != len(self.reason_codes):
            raise ValueError("reason_codes must not repeat")
        allowed = self.decision is Decision.ALLOW
        if allowed and self.execution_token is None:
            raise ValueError("an ALLOW decision must carry an execution token")
        if not allowed and self.execution_token is not None:
            raise ValueError("only an ALLOW decision may carry an execution token")
        if self.decision is Decision.HUMAN_REVIEW and self.approval_id is None:
            raise ValueError("a HUMAN_REVIEW decision must carry an approval_id")
        return self

    @property
    def permits_execution(self) -> bool:
        """True when the action may go ahead now."""
        return self.decision is Decision.ALLOW
