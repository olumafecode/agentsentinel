"""A fake gateway that answers Vera with chosen decisions, for testing the agent loop."""

import json
from datetime import UTC, datetime

import httpx2
import pytest

from banking_agent.agent import SessionContext, Vera
from banking_agent.gateway import GatewayClient
from sentinel_contracts import (
    ActionOutcome,
    Decision,
    ExecutionResult,
    GovernanceDecision,
    ReasonCode,
    TaskType,
)

NOW = 1_800_000_000.0
RESULTS = {
    "get_transactions": [
        {"transaction_id": "TXN-0000004568"},
        {"transaction_id": "TXN-0000004569"},
    ],
    "get_customer": {"customer_id": "CUS-000123", "full_name": "Avery Stone"},
    "issue_refund": {"amount": "120.00", "account_id": "ACC-00000123"},
}
REASONS = {
    Decision.ALLOW: ReasonCode.WITHIN_POLICY,
    Decision.HUMAN_REVIEW: ReasonCode.REFUND_OVER_LIMIT,
    Decision.BLOCK: ReasonCode.OUTSIDE_CUSTOMER_SCOPE,
    Decision.QUARANTINE: ReasonCode.AGENT_QUARANTINED,
}


def outcome_for(body, decision):
    allowed = decision is Decision.ALLOW
    when = datetime.fromtimestamp(NOW, tz=UTC)
    governance = GovernanceDecision(
        correlation_id=body["correlation_id"],
        decision=decision,
        reason_codes=[REASONS[decision]],
        summary=f"Decided {decision.value}.",
        approval_id="APR-000007" if decision is Decision.HUMAN_REVIEW else None,
        execution_token="v1.token.signature" if allowed else None,
        decided_at=when,
    )
    execution = None
    if allowed:
        execution = ExecutionResult(
            status="succeeded",
            tool_name=body["tool_name"],
            http_status=200,
            result=RESULTS.get(body["tool_name"], {}),
            completed_at=when,
        )
    return ActionOutcome(decision=governance, execution=execution)


class FakeGateway:
    """Decides by tool name. ``decisions`` maps a tool to a Decision, an HTTP status
    to answer with instead, or an exception to raise; anything else is allowed."""

    def __init__(self):
        self.decisions = {}
        self.requests = []

    def handler(self, request):
        body = json.loads(request.content)
        self.requests.append((request, body))
        answer = self.decisions.get(body["tool_name"], Decision.ALLOW)
        if isinstance(answer, list):
            answer = answer.pop(0) if len(answer) > 1 else answer[0]
        if isinstance(answer, Exception):
            raise answer
        if isinstance(answer, int):
            return httpx2.Response(
                answer, json={"error": {"code": f"http_{answer}", "message": "refused"}}
            )
        return httpx2.Response(200, content=outcome_for(body, answer).model_dump_json())

    @property
    def tools_called(self):
        return [body["tool_name"] for _, body in self.requests]


@pytest.fixture
def fake_gateway():
    return FakeGateway()


@pytest.fixture
def client(fake_gateway):
    return GatewayClient(
        "http://gateway.test",
        "vera-agent-key-0123456789abcdef0123456",
        client=httpx2.Client(transport=httpx2.MockTransport(fake_gateway.handler)),
        sleep=lambda seconds: None,
    )


@pytest.fixture
def vera(client):
    return Vera(client, agent_id="AGT-001", clock=lambda: NOW)


@pytest.fixture
def session():
    return SessionContext(
        session_id="SES-00000042",
        customer_id="CUS-000123",
        task_type=TaskType.ACCOUNT_INQUIRY,
        token="s1.session.token",
    )
