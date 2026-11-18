"""The context checks that run before any bank rule (US-18.2, US-18.3)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from sentinel_contracts import (
    Decision,
    ProtectedActionRequest,
    ReasonCode,
    SessionClaims,
)
from sentinel_gateway.checks import (
    MAX_CLOCK_AHEAD,
    MAX_REQUEST_AGE,
    ActionContext,
    AgentStatusCheck,
    ContextBindingCheck,
    KnownToolCheck,
    RequestFreshnessCheck,
)
from sentinel_gateway.registry import AgentRegistry, AgentStatus, ToolRegistry

RECEIVED = datetime(2027, 1, 15, 8, 0, tzinfo=UTC)
VERA = AgentRegistry.load().get("AGT-001")
TOOLS = ToolRegistry.load()

SESSION = SessionClaims(
    session_id="SES-00000042",
    customer_id="CUS-000123",
    agent_id="AGT-001",
    task_type="account_inquiry",
    channel="web_chat",
    issuer="veridane-identity",
    audience="sentinel-gateway",
    issued_at=int(RECEIVED.timestamp()) - 60,
    expires_at=int(RECEIVED.timestamp()) + 1740,
)


def context(
    *, session=SESSION, session_error=None, agent=VERA, agent_id="AGT-001", **changes
):
    """An action in the standard session, with any request fields changed."""
    fields = {
        "correlation_id": str(uuid.uuid4()),
        "session_id": "SES-00000042",
        "agent_id": "AGT-001",
        "customer_scope": "CUS-000123",
        "task_type": "account_inquiry",
        "tool_name": "get_customer",
        "arguments": {"customer_id": "CUS-000123"},
        "provenance_labels": {"customer_id": "system"},
        "requested_at": RECEIVED,
    }
    request = ProtectedActionRequest(**{**fields, **changes})
    return ActionContext(
        request=request,
        agent_id=agent_id,
        agent=agent,
        tool=TOOLS.get(request.tool_name),
        session=session,
        session_error=session_error,
        received_at=RECEIVED,
    )


@pytest.mark.parametrize(
    "check",
    [
        ContextBindingCheck(),
        AgentStatusCheck(),
        RequestFreshnessCheck(),
        KnownToolCheck(),
    ],
)
def test_a_well_formed_action_in_its_own_session_passes(check):
    assert not check.evaluate(context(), []).objects


class TestContextBinding:
    check = ContextBindingCheck()

    def test_the_agent_in_the_request_must_be_the_caller(self):
        finding = self.check.evaluate(context(agent_id="AGT-002"), [])

        assert finding.decision is Decision.BLOCK
        assert finding.reasons == (ReasonCode.IDENTITY_MISMATCH,)
        assert finding.details == {"field": "agent_id"}

    @pytest.mark.parametrize(
        ("session_error", "reason"),
        [
            (None, ReasonCode.MISSING_CONTEXT),
            ("session_expired", ReasonCode.MISSING_CONTEXT),
            ("session_not_yet_valid", ReasonCode.MISSING_CONTEXT),
            ("session_signature_invalid", ReasonCode.IDENTITY_MISMATCH),
            ("session_malformed", ReasonCode.IDENTITY_MISMATCH),
        ],
    )
    def test_an_action_needs_a_verified_session(self, session_error, reason):
        finding = self.check.evaluate(
            context(session=None, session_error=session_error), []
        )

        assert finding.decision is Decision.BLOCK
        assert finding.reasons == (reason,)
        assert finding.details == {"session_error": session_error or "session_missing"}

    def test_every_difference_from_the_session_is_named(self):
        finding = self.check.evaluate(
            context(customer_scope="CUS-000456", task_type="refund_request"), []
        )

        assert finding.reasons == (ReasonCode.IDENTITY_MISMATCH,)
        assert finding.details == {"fields": ["customer_scope", "task_type"]}

    def test_a_session_for_another_agent_does_not_bind(self):
        other = SESSION.model_copy(update={"agent_id": "AGT-002"})

        finding = self.check.evaluate(context(session=other), [])

        assert finding.details == {"fields": ["agent_id"]}


class TestAgentStatus:
    check = AgentStatusCheck()

    def test_an_unregistered_agent_is_blocked(self):
        finding = self.check.evaluate(context(agent=None), [])

        assert finding.decision is Decision.BLOCK
        assert finding.reasons == (ReasonCode.IDENTITY_MISMATCH,)

    @pytest.mark.parametrize(
        ("status", "decision", "reason"),
        [
            (
                AgentStatus.QUARANTINED,
                Decision.QUARANTINE,
                ReasonCode.AGENT_QUARANTINED,
            ),
            (AgentStatus.DISABLED, Decision.BLOCK, ReasonCode.AGENT_DISABLED),
        ],
    )
    def test_an_agent_that_is_not_active_cannot_act(self, status, decision, reason):
        agent = VERA.model_copy(update={"status": status})

        finding = self.check.evaluate(context(agent=agent), [])

        assert finding.decision is decision
        assert finding.reasons == (reason,)
        assert "Vera" in finding.summary


class TestRequestFreshness:
    check = RequestFreshnessCheck()

    @pytest.mark.parametrize(
        ("offset", "fresh"),
        [
            (-MAX_REQUEST_AGE, True),
            (-MAX_REQUEST_AGE - timedelta(seconds=1), False),
            (MAX_CLOCK_AHEAD, True),
            (MAX_CLOCK_AHEAD + timedelta(seconds=1), False),
        ],
    )
    def test_the_request_time_must_be_close_to_now(self, offset, fresh):
        finding = self.check.evaluate(context(requested_at=RECEIVED + offset), [])

        assert finding.objects is not fresh
        if not fresh:
            assert finding.reasons == (ReasonCode.STALE_REQUEST,)


class TestKnownTool:
    check = KnownToolCheck()

    def test_a_tool_missing_from_the_registry_is_blocked(self):
        finding = self.check.evaluate(context(tool_name="wire_transfer"), [])

        assert finding.decision is Decision.BLOCK
        assert finding.reasons == (ReasonCode.UNKNOWN_TOOL,)
        assert "wire_transfer" in finding.summary
