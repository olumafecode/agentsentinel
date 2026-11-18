"""Vera's gateway client: credentials, retries that are safe, and errors (US-17.1)."""

import json
import uuid
from datetime import UTC, datetime

import httpx2
import pytest

from banking_agent.gateway import GatewayClient, GatewayRefused, GatewayUnavailable
from sentinel_contracts import Decision, ProtectedActionRequest

REQUEST = ProtectedActionRequest(
    correlation_id=str(uuid.uuid4()),
    session_id="SES-00000042",
    agent_id="AGT-001",
    customer_scope="CUS-000123",
    task_type="account_inquiry",
    tool_name="get_customer",
    arguments={"customer_id": "CUS-000123"},
    provenance_labels={"customer_id": "system"},
    requested_at=datetime(2027, 1, 15, 8, tzinfo=UTC),
)


def test_the_action_goes_to_the_evaluate_endpoint_with_both_credentials(
    client, fake_gateway
):
    outcome = client.evaluate(REQUEST, "s1.session.token")

    [(request, body)] = fake_gateway.requests
    assert str(request.url) == "http://gateway.test/v1/actions/evaluate"
    assert (
        request.headers["Authorization"]
        == "Bearer vera-agent-key-0123456789abcdef0123456"
    )
    assert request.headers["X-Session-Token"] == "s1.session.token"
    assert body == REQUEST.model_dump(mode="json")
    assert outcome.decision.decision is Decision.ALLOW


@pytest.mark.parametrize(
    "failures",
    [
        [httpx2.ConnectError("refused")],
        [503],
        [httpx2.ReadTimeout("slow"), 503],
    ],
)
def test_a_lost_or_unaudited_call_is_sent_again_unchanged(
    client, fake_gateway, failures
):
    fake_gateway.decisions["get_customer"] = [*failures, Decision.ALLOW]

    outcome = client.evaluate(REQUEST, "s1.session.token")

    assert outcome.decision.decision is Decision.ALLOW
    bodies = [body for _, body in fake_gateway.requests]
    assert len(bodies) == len(failures) + 1
    assert all(body == bodies[0] for body in bodies)


def test_the_client_gives_up_after_its_retries(client, fake_gateway):
    fake_gateway.decisions["get_customer"] = [503]

    with pytest.raises(GatewayUnavailable) as caught:
        client.evaluate(REQUEST, "s1.session.token")

    assert caught.value.code == "http_503"
    assert len(fake_gateway.requests) == 3


@pytest.mark.parametrize("status", [400, 401, 409, 413])
def test_a_refused_request_is_not_retried(client, fake_gateway, status):
    fake_gateway.decisions["get_customer"] = [status]

    with pytest.raises(GatewayRefused) as caught:
        client.evaluate(REQUEST, "s1.session.token")

    assert caught.value.status_code == status
    assert len(fake_gateway.requests) == 1


def test_an_answer_that_is_not_an_outcome_is_refused():
    def handler(request):
        return httpx2.Response(200, content=json.dumps({"decision": "yes"}))

    client = GatewayClient(
        "http://gateway.test",
        "key",
        client=httpx2.Client(transport=httpx2.MockTransport(handler)),
    )

    with pytest.raises(GatewayRefused, match="could not be read"):
        client.evaluate(REQUEST, "s1.session.token")
