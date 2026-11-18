"""Health, documentation, start-up checks and held actions."""

import pytest

from sentinel_contracts import Decision, ReasonCode
from sentinel_gateway.checks import Check, Stage, objection
from sentinel_gateway.config import ConfigError
from sentinel_gateway.main import create_app
from sentinel_gateway.pipeline import default_checks
from sentinel_gateway.registry import AgentRegistry


class LargeRefundRule(Check):
    """Stands in for the US-03 rule: every refund needs a person's approval."""

    name = "large_refund"
    stage = Stage.MANDATORY_REVIEW

    def evaluate(self, context, earlier):
        return objection(
            Decision.HUMAN_REVIEW,
            ReasonCode.REFUND_OVER_LIMIT,
            summary="Refunds need a person's approval.",
        )


class Approvals:
    def __init__(self, approval_id="APR-000007"):
        self.approval_id = approval_id
        self.requests = []

    def request_approval(self, request, verdict):
        self.requests.append((request.correlation_id, verdict.reasons))
        if isinstance(self.approval_id, Exception):
            raise self.approval_id
        return self.approval_id


def test_liveness_and_readiness(gateway):
    assert gateway.get("/healthz").json() == {"status": "ok"}
    assert gateway.get("/readyz").json() == {
        "status": "ready",
        "agents": 2,
        "tools": 9,
        "checks": [
            "context_binding",
            "agent_status",
            "request_freshness",
            "known_tool",
            "tool_allowlist",
            "customer_scope",
        ],
    }


def test_the_api_documentation_describes_the_request_and_every_reference_resolves(
    gateway,
):
    schema = gateway.get("/openapi.json").json()
    operation = schema["paths"]["/v1/actions/evaluate"]["post"]
    components = schema["components"]["schemas"]

    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ProtectedActionRequest"
    }
    assert operation["security"] == [{"AgentKey": []}]
    assert schema["components"]["securitySchemes"]["AgentKey"]["scheme"] == "bearer"
    assert "provenance_labels" in components["ProtectedActionRequest"]["properties"]

    def references(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "$ref":
                    yield value
                else:
                    yield from references(value)
        elif isinstance(node, list):
            for item in node:
                yield from references(item)

    for ref in references(schema):
        assert ref.startswith("#/components/schemas/")
        assert ref.rsplit("/", 1)[1] in components, ref


def test_a_key_for_an_unregistered_agent_stops_the_gateway(settings, bank):
    only_vera = AgentRegistry([AgentRegistry.load().get("AGT-001")])

    with pytest.raises(ConfigError, match="AGT-002"):
        create_app(settings, agents=only_vera, bank_client=bank)


def test_a_held_action_is_blocked_while_there_is_no_approval_service(
    make_gateway, evaluate, refund, refund_session, bank, audit, ownership
):
    gateway = make_gateway(
        checks=[*default_checks(ownership=ownership), LargeRefundRule()]
    )
    body = refund()

    decision = evaluate(body, session=refund_session, client=gateway).json()["decision"]

    assert decision["decision"] == "BLOCK"
    assert decision["reason_codes"] == ["DEPENDENCY_UNAVAILABLE", "REFUND_OVER_LIMIT"]
    assert "approval service is not available" in decision["summary"]
    assert bank.calls == []
    assert (
        audit.for_correlation(body["correlation_id"])[-1].event_type == "action_stopped"
    )


def test_a_held_action_opens_an_approval_and_does_not_run(
    make_gateway, evaluate, refund, refund_session, bank, audit, ownership
):
    approvals = Approvals()
    gateway = make_gateway(
        checks=[*default_checks(ownership=ownership), LargeRefundRule()],
        approvals=approvals,
    )
    body = refund()

    outcome = evaluate(body, session=refund_session, client=gateway).json()

    assert outcome["decision"]["decision"] == "HUMAN_REVIEW"
    assert outcome["decision"]["approval_id"] == "APR-000007"
    assert outcome["decision"]["execution_token"] is None
    assert outcome["execution"] is None
    assert approvals.requests == [
        (body["correlation_id"], (ReasonCode.REFUND_OVER_LIMIT,))
    ]
    assert bank.calls == []
    final = audit.for_correlation(body["correlation_id"])[-1]
    assert final.event_type == "approval_requested"
    assert final.payload["approval_id"] == "APR-000007"


@pytest.mark.parametrize("failure", [ConnectionError("down"), "not-an-approval-id"])
def test_a_failing_approval_service_blocks_the_held_action(
    make_gateway, evaluate, refund, refund_session, bank, ownership, failure
):
    gateway = make_gateway(
        checks=[*default_checks(ownership=ownership), LargeRefundRule()],
        approvals=Approvals(failure),
    )

    decision = evaluate(refund(), session=refund_session, client=gateway).json()[
        "decision"
    ]

    assert decision["decision"] == "BLOCK"
    assert decision["reason_codes"][0] == "DEPENDENCY_UNAVAILABLE"
    assert bank.calls == []


def test_every_evaluated_action_leaves_a_complete_audit_trail(evaluate, action, audit):
    allowed, blocked = action(), action(tool_name="wire_transfer")
    evaluate(allowed)
    evaluate(blocked)

    trail = audit.for_correlation(allowed["correlation_id"])
    assert [e.event_type for e in trail] == [
        "action_received",
        "decision_made",
        "action_executed",
    ]
    received, decided, executed = trail
    assert received.payload["authenticated_agent_id"] == "AGT-001"
    assert received.payload["session"]["customer_id"] == "CUS-000123"
    assert received.payload["request"] == allowed
    assert decided.decision == "ALLOW"
    assert decided.payload["reason_codes"] == ["WITHIN_POLICY"]
    assert [c["check"] for c in decided.payload["checks"]] == [
        "context_binding",
        "agent_status",
        "request_freshness",
        "known_tool",
        "tool_allowlist",
        "customer_scope",
    ]
    assert executed.payload == {
        "tool_name": "get_transactions",
        "status": "succeeded",
        "http_status": 200,
        "error": None,
    }
    assert all(e.actor == "sentinel-gateway" for e in trail)

    stopped = audit.for_correlation(blocked["correlation_id"])[-1]
    assert stopped.event_type == "action_stopped"
    assert stopped.decision == "BLOCK"
    assert stopped.payload == {"reason_codes": ["UNKNOWN_TOOL"]}


def test_no_audit_record_holds_a_token(evaluate, action, audit, session_token):
    token = session_token()
    outcome = evaluate(action(), session=token).json()

    text = " ".join(event.model_dump_json() for event in audit.events)
    assert token not in text
    assert outcome["decision"]["execution_token"] not in text
