"""Synthetic data schema for AgentSentinel (proposal Section 7.4).

Every service, generator and test uses these models so the invented bank data has one shape.
The patterns below also enforce the synthetic-data rules in data/synthetic/README.md:
reserved email domains, the fictional 555-01xx phone range and prefixed identifiers.
"""
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

SCHEMA_VERSION = "1.0.0"

# ---------------------------------------------------------------- identifier and value formats
CustomerId = Annotated[str, StringConstraints(pattern=r"^CUS-\d{6}$")]
AccountId = Annotated[str, StringConstraints(pattern=r"^ACC-\d{8}$")]
TransactionId = Annotated[str, StringConstraints(pattern=r"^TXN-\d{10}$")]
AgentId = Annotated[str, StringConstraints(pattern=r"^AGT-\d{3}$")]
StaffId = Annotated[str, StringConstraints(pattern=r"^USR-\d{4}$")]
SessionId = Annotated[str, StringConstraints(pattern=r"^SES-\d{8}$")]
ApprovalId = Annotated[str, StringConstraints(pattern=r"^APR-\d{6}$")]
IncidentId = Annotated[str, StringConstraints(pattern=r"^INC-\d{6}$")]
EventId = Annotated[str, StringConstraints(pattern=r"^EVT-\d{6}$")]
CorrelationId = Annotated[
    str, StringConstraints(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
SemVer = Annotated[str, StringConstraints(pattern=r"^\d+\.\d+\.\d+$")]
ToolName = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{2,40}$")]
UseCaseId = Annotated[str, StringConstraints(pattern=r"^UC-\d{2}$")]
SyntheticEmail = Annotated[str, StringConstraints(pattern=r"^[a-z0-9._+-]+@example\.(com|org|net)$")]
SyntheticPhone = Annotated[str, StringConstraints(pattern=r"^\+1-555-01\d{2}$")]
Money = Annotated[Decimal, Field(max_digits=12, decimal_places=2)]


# ---------------------------------------------------------------- enumerations
class Decision(str, Enum):
    ALLOW = "ALLOW"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    BLOCK = "BLOCK"
    QUARANTINE = "QUARANTINE"


class FailureMode(str, Enum):
    NONE = "none"
    PROMPT_INJECTION = "prompt_injection"
    MISUNDERSTOOD_INSTRUCTION = "misunderstood_instruction"
    WRONG_TOOL_OR_INVALID_DETAILS = "wrong_tool_or_invalid_details"
    OUTSIDE_AUTHORITY = "outside_authority"
    UNINTENDED_SEQUENCE = "unintended_sequence"


class Provenance(str, Enum):
    TRUSTED_USER_INPUT = "trusted_user_input"
    UNTRUSTED_CONTENT = "untrusted_content"
    SYSTEM = "system"


class TaskType(str, Enum):
    ACCOUNT_INQUIRY = "account_inquiry"
    REFUND_REQUEST = "refund_request"
    PROFILE_UPDATE = "profile_update"
    DISPUTE = "dispute"
    ADMIN_MAINTENANCE = "admin_maintenance"


class ToolCategory(str, Enum):
    READ = "read"
    WRITE = "write"
    FINANCIAL = "financial"
    EXPORT = "export"
    ADMIN = "admin"


class AgentStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    QUARANTINED = "quarantined"


class AccountType(str, Enum):
    CHECKING = "checking"
    SAVINGS = "savings"


class AccountStatus(str, Enum):
    OPEN = "open"
    FROZEN = "frozen"
    CLOSED = "closed"


class TransactionType(str, Enum):
    PURCHASE = "purchase"
    DEPOSIT = "deposit"
    TRANSFER = "transfer"
    FEE = "fee"
    REFUND = "refund"


class RiskBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class AuditEventType(str, Enum):
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


class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class DatasetSplit(str, Enum):
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"


class Entity(BaseModel):
    """Base for every record: unknown fields are rejected and records cannot be changed after creation."""

    model_config = ConfigDict(extra="forbid", frozen=True)


# ---------------------------------------------------------------- the demo bank
class Customer(Entity):
    customer_id: CustomerId = Field(description="Customer identifier")
    full_name: str = Field(min_length=3, max_length=80, description="Invented name from the seeded generator")
    email: SyntheticEmail = Field(description="Always at a reserved example domain")
    phone: SyntheticPhone = Field(description="Always in the fictional 555-01xx range")
    created_at: AwareDatetime = Field(description="When the customer record was created (UTC)")


class Account(Entity):
    account_id: AccountId = Field(description="Account identifier")
    customer_id: CustomerId = Field(description="Owner of the account")
    account_type: AccountType = Field(description="checking or savings")
    currency: Annotated[str, StringConstraints(pattern=r"^USD$")] = Field(description="Demo bank holds USD only")
    balance: Money = Field(ge=0, description="Current balance")
    status: AccountStatus = Field(description="open, frozen or closed")
    opened_at: AwareDatetime = Field(description="When the account was opened (UTC)")


class Transaction(Entity):
    transaction_id: TransactionId = Field(description="Transaction identifier")
    account_id: AccountId = Field(description="Account the transaction belongs to")
    transaction_type: TransactionType = Field(description="purchase, deposit, transfer, fee or refund")
    amount: Money = Field(gt=0, description="Positive amount; the type gives the direction")
    currency: Annotated[str, StringConstraints(pattern=r"^USD$")] = Field(description="USD")
    description: str = Field(max_length=140, description="Short invented description")
    related_transaction_id: TransactionId | None = Field(
        default=None, description="For a refund, the purchase being refunded"
    )
    created_at: AwareDatetime = Field(description="When the transaction was posted (UTC)")

    @model_validator(mode="after")
    def refund_points_to_a_purchase(self):
        if self.transaction_type is TransactionType.REFUND and self.related_transaction_id is None:
            raise ValueError("a refund must name the transaction it refunds")
        return self


# ---------------------------------------------------------------- agents, tools and sessions
class Agent(Entity):
    agent_id: AgentId = Field(description="Agent identifier in the registry")
    name: str = Field(min_length=2, max_length=40, description="Display name, for example Vera")
    role: str = Field(min_length=3, max_length=40, description="Role that policy uses, for example customer_service")
    allowed_tools: list[ToolName] = Field(min_length=1, description="Tools this agent may ever propose")
    status: AgentStatus = Field(description="active, disabled or quarantined")
    review_threshold: float = Field(ge=0, le=1, description="Risk score at or above this goes to human review")
    block_threshold: float = Field(ge=0, le=1, description="Risk score at or above this is blocked")
    created_at: AwareDatetime = Field(description="When the agent was registered (UTC)")

    @model_validator(mode="after")
    def thresholds_are_ordered(self):
        if self.review_threshold > self.block_threshold:
            raise ValueError("review_threshold must not be higher than block_threshold")
        return self


class ToolDefinition(Entity):
    tool_name: ToolName = Field(description="Name the agent uses to call the tool")
    category: ToolCategory = Field(description="read, write, financial, export or admin")
    description: str = Field(max_length=200, description="What the tool does")
    high_impact: bool = Field(description="True when a wrong call could move money or expose data")
    sensitive_parameters: list[str] = Field(description="Arguments whose origin must be tracked")
    allowed_task_types: list[TaskType] = Field(description="Tasks for which the tool may be used")


class UserSession(Entity):
    session_id: SessionId = Field(description="Session identifier")
    customer_id: CustomerId = Field(description="The signed-in customer the agent is serving")
    agent_id: AgentId = Field(description="Agent handling the session")
    channel: str = Field(min_length=2, max_length=20, description="Where the session runs, for example web_chat")
    task_type: TaskType = Field(description="What the customer asked for")
    started_at: AwareDatetime = Field(description="Session start (UTC)")
    expires_at: AwareDatetime = Field(description="Session end (UTC)")

    @model_validator(mode="after")
    def session_has_positive_length(self):
        if self.expires_at <= self.started_at:
            raise ValueError("expires_at must be after started_at")
        return self


class ToolCall(Entity):
    """One protected action proposed by the agent (the ProtectedActionRequest of proposal Appendix E)."""

    correlation_id: CorrelationId = Field(description="UUID version 4 that ties every record of this action together")
    session_id: SessionId = Field(description="Session the action belongs to")
    agent_id: AgentId = Field(description="Agent proposing the action")
    customer_scope: CustomerId = Field(description="Customer the session is bound to")
    task_type: TaskType = Field(description="Task the agent is working on")
    tool_name: ToolName = Field(description="Tool the agent wants to call")
    arguments: dict[str, Any] = Field(description="Structured tool arguments")
    provenance_labels: dict[str, Provenance] = Field(
        description="Origin of each argument: trusted_user_input, untrusted_content or system"
    )
    requested_at: AwareDatetime = Field(description="When the agent proposed the action (UTC)")

    @model_validator(mode="after")
    def labels_refer_to_arguments(self):
        unknown = set(self.provenance_labels) - set(self.arguments)
        if unknown:
            raise ValueError(f"provenance labels for arguments that do not exist: {sorted(unknown)}")
        return self


# ---------------------------------------------------------------- decisions and evidence
class PolicyVersion(Entity):
    policy_version: SemVer = Field(description="Version of the OPA policy bundle")
    bundle_checksum: Sha256 = Field(description="SHA-256 of the bundle")
    description: str = Field(max_length=200, description="What changed in this version")
    is_active: bool = Field(description="True for the bundle the gateway uses now")
    activated_at: AwareDatetime | None = Field(default=None, description="When it became active (UTC)")


class RiskAssessment(Entity):
    correlation_id: CorrelationId = Field(description="Action that was scored")
    model_version: SemVer = Field(description="Version of the risk model")
    feature_schema_version: SemVer = Field(description="Version of the feature layout the model expects")
    risk_score: float = Field(ge=0, le=1, description="0 is safe, 1 is most risky")
    risk_band: RiskBand = Field(description="low, medium or high")
    top_features: list[str] = Field(description="Features that contributed most, where the model supports it")
    assessed_at: AwareDatetime = Field(description="When the score was produced (UTC)")


class ApprovalRequest(Entity):
    approval_id: ApprovalId = Field(description="Approval request identifier")
    correlation_id: CorrelationId = Field(description="Held action")
    requested_by: AgentId = Field(description="Agent whose action is held")
    reason: str = Field(max_length=300, description="Why the action needs a person")
    status: ApprovalStatus = Field(description="pending, approved, rejected or expired")
    approver_id: StaffId | None = Field(default=None, description="Staff member who decided")
    created_at: AwareDatetime = Field(description="When the request was raised (UTC)")
    expires_at: AwareDatetime = Field(description="When an undecided request lapses (UTC)")
    decided_at: AwareDatetime | None = Field(default=None, description="When it was decided (UTC)")

    @model_validator(mode="after")
    def decision_fields_are_consistent(self):
        decided = self.status in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED)
        if decided and (self.approver_id is None or self.decided_at is None):
            raise ValueError("an approved or rejected request needs approver_id and decided_at")
        if not decided and (self.approver_id is not None or self.decided_at is not None):
            raise ValueError("a pending or expired request must not carry an approver or decision time")
        return self


class AuditEvent(Entity):
    event_id: EventId = Field(description="Position of the event in the chain")
    correlation_id: CorrelationId = Field(description="Action the event describes")
    event_type: AuditEventType = Field(description="What happened")
    actor: str = Field(min_length=3, max_length=40, description="Service, agent or staff member that acted")
    decision: Decision | None = Field(default=None, description="Outcome, on decision events")
    policy_version: SemVer | None = Field(default=None, description="Policy bundle in force")
    model_version: SemVer | None = Field(default=None, description="Risk model in force")
    payload: dict[str, Any] = Field(description="Decision inputs and results for this step")
    created_at: AwareDatetime = Field(description="When the event was written (UTC)")
    previous_event_hash: Sha256 = Field(description="Hash of the event before this one; 64 zeros for the first")
    event_hash: Sha256 = Field(description="SHA-256 over this event's content and previous_event_hash")


class Incident(Entity):
    incident_id: IncidentId = Field(description="Incident identifier")
    agent_id: AgentId = Field(description="Agent involved")
    correlation_ids: list[CorrelationId] = Field(min_length=1, description="Actions that make up the incident")
    severity: IncidentSeverity = Field(description="low, medium, high or critical")
    status: IncidentStatus = Field(description="open or closed")
    summary: str = Field(max_length=300, description="One-line description for the dashboard")
    opened_at: AwareDatetime = Field(description="When the incident was opened (UTC)")
    closed_at: AwareDatetime | None = Field(default=None, description="When it was closed (UTC)")


class ExplanationEvidence(Entity):
    correlation_id: CorrelationId = Field(description="Decision being explained")
    plain_english_reason: str = Field(max_length=800, description="Explanation shown to analysts and approvers")
    evidence_ids: list[str] = Field(min_length=1, description="Policy section IDs the explanation cites")
    provider_model_version: str = Field(max_length=80, description="LLM provider and model used, or mock")
    generated_at: AwareDatetime = Field(description="When the explanation was generated (UTC)")


# ---------------------------------------------------------------- labelled events for the risk model
class LabelledActionEvent(Entity):
    """One row of the training and evaluation dataset (story US-21). Labelling rules: labelling-rules.md."""

    event_id: EventId = Field(description="Row identifier")
    sequence_id: Annotated[str, StringConstraints(pattern=r"^SEQ-\d{6}$")] = Field(
        description="Groups the actions of one session into a sequence"
    )
    position: int = Field(ge=1, description="Order of the action inside its sequence, starting at 1")
    tool_call: ToolCall = Field(description="The proposed action")
    expected_outcome: Decision = Field(description="Label: what AgentSentinel should decide")
    failure_mode: FailureMode = Field(description="Label: which failure mode this is, or none")
    use_case: UseCaseId | None = Field(default=None, description="Use case the scenario comes from")
    rule: str = Field(min_length=2, max_length=10, description="Labelling rule that set the outcome, for example R3")
    split: DatasetSplit | None = Field(default=None, description="train, validation or test, set once and frozen")

    @model_validator(mode="after")
    def normal_actions_are_allowed(self):
        if self.failure_mode is FailureMode.NONE and self.expected_outcome in (Decision.BLOCK, Decision.QUARANTINE):
            raise ValueError("a blocked or quarantined event must name its failure mode")
        return self


ENTITIES = {
    m.__name__: m
    for m in (
        Customer, Account, Transaction, Agent, ToolDefinition, UserSession, ToolCall, PolicyVersion,
        RiskAssessment, ApprovalRequest, AuditEvent, Incident, ExplanationEvidence, LabelledActionEvent,
    )
}
