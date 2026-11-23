"""The bank policy in OPA: the client, the check, and the real policy (US-02a).

The first tests stand OPA in with a mock transport. The tests that use ``opa_url``
run the real policies from policies/opa in a real OPA server; they are skipped where
the opa command is not installed, and fail in CI if it is missing.
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx2
import pytest

from sentinel_contracts import Decision, ProtectedActionRequest, ReasonCode
from sentinel_gateway.checks import ActionContext
from sentinel_gateway.policy import (
    DECISION_PATH,
    OpaClient,
    PolicyAnswer,
    PolicyCheck,
    PolicyUnavailable,
    Violation,
    policy_input,
)
from sentinel_gateway.registry import AgentRegistry, ToolRegistry

RECEIVED = datetime(2027, 1, 15, 8, 0, tzinfo=UTC)
VERA = AgentRegistry.load().get("AGT-001")
TOOLS = ToolRegistry.load()
MANIFEST = Path(__file__).resolve().parents[3] / "policies" / "opa" / ".manifest"
BUNDLE_VERSION = json.loads(MANIFEST.read_text(encoding="utf-8"))["revision"]

BULK = {
    "rule": "bulk_export",
    "decision": "BLOCK",
    "reason": "POLICY_DENY",
    "message": "Exporting customer records in bulk is never allowed through an agent.",
}
FOR_TASK = {
    "rule": "tool_not_allowed_for_task",
    "decision": "BLOCK",
    "reason": "TOOL_NOT_ALLOWED",
    "message": "export_customers is not allowed for account_inquiry tasks.",
}
REVIEW = {
    "rule": "refund_above_automatic_limit",
    "decision": "HUMAN_REVIEW",
    "reason": "REFUND_OVER_LIMIT",
    "message": "Refunds above 200.00 USD need a person's approval.",
}


def refund_arguments(amount="120.00", account="ACC-00000123"):
    return {
        "account_id": account,
        "amount": amount,
        "original_transaction_id": "TXN-0000004568",
        "reason": "Duplicate charge",
    }


def context(tool_name="get_transactions", task="account_inquiry", arguments=None):
    request = ProtectedActionRequest(
        correlation_id=str(uuid.uuid4()),
        session_id="SES-00000042",
        agent_id="AGT-001",
        customer_scope="CUS-000123",
        task_type=task,
        tool_name=tool_name,
        arguments={"customer_id": "CUS-000123"} if arguments is None else arguments,
        provenance_labels={},
        requested_at=RECEIVED,
    )
    return ActionContext(
        request=request,
        agent_id="AGT-001",
        agent=VERA,
        tool=TOOLS.get(tool_name),
        session=None,
        session_error=None,
        received_at=RECEIVED,
    )


def opa_answer(*violations, bundles=None):
    return {
        "result": {"violations": list(violations)},
        "provenance": {
            "version": "1.22.4",
            "bundles": {"/policies": {"revision": "1.4.2"}}
            if bundles is None
            else bundles,
        },
    }


def mock_opa(handler):
    seen = []

    def record(request):
        seen.append(request)
        return handler(request)

    client = httpx2.Client(transport=httpx2.MockTransport(record))
    return OpaClient("http://opa.test", client=client), seen


class FixedPolicy:
    def __init__(self, *violations, version="1.4.2"):
        self.answer = PolicyAnswer(
            version=version,
            violations=tuple(Violation.model_validate(v) for v in violations),
        )
        self.inputs = []

    def evaluate(self, document):
        self.inputs.append(document)
        return self.answer

    def ready(self):
        return True


class TestOpaClient:
    def test_it_asks_for_the_decision_with_the_bundle_version(self):
        opa, seen = mock_opa(lambda r: httpx2.Response(200, json=opa_answer(BULK)))

        answer = opa.evaluate({"action": {"tool_name": "export_customers"}})

        assert answer.version == "1.4.2"
        assert answer.violations == (Violation.model_validate(BULK),)
        (request,) = seen
        assert request.method == "POST"
        assert request.url.path == DECISION_PATH
        assert request.url.params["provenance"] == "true"
        assert json.loads(request.content) == {
            "input": {"action": {"tool_name": "export_customers"}}
        }

    def test_no_violations_is_an_answer_too(self):
        opa, _ = mock_opa(lambda r: httpx2.Response(200, json=opa_answer()))

        assert opa.evaluate({}) == PolicyAnswer(version="1.4.2", violations=())

    @pytest.mark.parametrize(
        ("response", "message"),
        [
            (httpx2.Response(500, json={"code": "internal_error"}), "HTTP 500"),
            (httpx2.Response(200, text="not json"), "not JSON"),
            (httpx2.Response(200, json={}), "not loaded"),
            (httpx2.Response(200, json=[]), "not loaded"),
            (
                httpx2.Response(200, json={"result": {"violations": []}}),
                "no valid policy version",
            ),
            (
                httpx2.Response(200, json=opa_answer(bundles={})),
                "no valid policy version",
            ),
            (
                httpx2.Response(
                    200,
                    json=opa_answer(
                        bundles={
                            "a": {"revision": "1.0.0"},
                            "b": {"revision": "1.0.0"},
                        }
                    ),
                ),
                "no valid policy version",
            ),
            (
                httpx2.Response(
                    200, json=opa_answer(bundles={"/policies": {"revision": ""}})
                ),
                "no valid policy version",
            ),
            (
                httpx2.Response(200, json=opa_answer({**BULK, "decision": "ALLOW"})),
                "no valid policy version or violations",
            ),
            (
                httpx2.Response(200, json=opa_answer({**BULK, "reason": "MADE_UP"})),
                "no valid policy version or violations",
            ),
            (
                httpx2.Response(200, json=opa_answer({**BULK, "message": ""})),
                "no valid policy version or violations",
            ),
            (
                httpx2.Response(200, json=opa_answer({**BULK, "extra": 1})),
                "no valid policy version or violations",
            ),
        ],
    )
    def test_an_answer_it_cannot_trust_means_the_policy_is_unavailable(
        self, response, message
    ):
        opa, _ = mock_opa(lambda r: response)

        with pytest.raises(PolicyUnavailable, match=message):
            opa.evaluate({})

    @pytest.mark.parametrize(
        ("error", "message"),
        [
            (httpx2.ConnectError("refused"), "could not be reached"),
            (httpx2.ReadTimeout("slow"), "did not answer in time"),
        ],
    )
    def test_an_unreachable_or_slow_opa_means_the_policy_is_unavailable(
        self, error, message
    ):
        def fail(request):
            raise error

        opa, _ = mock_opa(fail)

        with pytest.raises(PolicyUnavailable, match=message):
            opa.evaluate({})

    @pytest.mark.parametrize(
        ("handler", "ready"),
        [
            (lambda r: httpx2.Response(200, json={}), True),
            (lambda r: httpx2.Response(500, json={}), False),
        ],
    )
    def test_ready_asks_opa_whether_the_bundle_is_active(self, handler, ready):
        opa, seen = mock_opa(handler)

        assert opa.ready() is ready
        assert seen[0].url.path == "/health"
        assert seen[0].url.params["bundles"] == "true"

    def test_an_unreachable_opa_is_not_ready(self):
        def fail(request):
            raise httpx2.ConnectError("refused")

        opa, _ = mock_opa(fail)

        assert opa.ready() is False


class TestPolicyCheck:
    def test_no_violations_means_no_objection_with_the_version_recorded(self):
        finding = PolicyCheck(FixedPolicy()).evaluate(context(), [])

        assert not finding.objects
        assert finding.policy_version == "1.4.2"
        assert finding.details == {"matched_rules": []}

    def test_the_strongest_rule_decides_and_every_reason_is_kept(self):
        policy = FixedPolicy(REVIEW, FOR_TASK, BULK)

        finding = PolicyCheck(policy).evaluate(context(), [])

        assert finding.decision is Decision.BLOCK
        assert finding.reasons == (
            ReasonCode.POLICY_DENY,
            ReasonCode.TOOL_NOT_ALLOWED,
            ReasonCode.REFUND_OVER_LIMIT,
        )
        assert finding.summary == BULK["message"]
        assert finding.policy_version == "1.4.2"
        assert finding.details == {
            "matched_rules": [
                "bulk_export",
                "tool_not_allowed_for_task",
                "refund_above_automatic_limit",
            ]
        }

    def test_a_rule_that_needs_a_person_asks_for_review(self):
        finding = PolicyCheck(FixedPolicy(REVIEW)).evaluate(context(), [])

        assert finding.decision is Decision.HUMAN_REVIEW
        assert finding.reasons == (ReasonCode.REFUND_OVER_LIMIT,)
        assert finding.summary == REVIEW["message"]

    def test_the_policy_sees_the_agent_the_tool_and_the_action(self):
        policy = FixedPolicy()
        refund = context("issue_refund", "refund_request", refund_arguments())

        PolicyCheck(policy).evaluate(refund, [])

        assert policy.inputs == [
            {
                "agent": {
                    "agent_id": "AGT-001",
                    "name": "Vera",
                    "allowed_tools": list(VERA.allowed_tools),
                },
                "tool": {
                    "tool_name": "issue_refund",
                    "category": "financial",
                    "high_impact": True,
                    "sensitive_parameters": ["account_id", "amount"],
                },
                "action": {
                    "task_type": "refund_request",
                    "tool_name": "issue_refund",
                    "customer_scope": "CUS-000123",
                    "arguments": refund_arguments(),
                    "provenance_labels": {},
                },
            }
        ]

    def test_without_an_agent_or_tool_there_is_nothing_to_ask(self):
        unknown = context(tool_name="wire_transfer")

        with pytest.raises(ValueError, match="registered agent and a known tool"):
            policy_input(unknown)


class TestTheRealPolicy:
    """The bank policy in policies/opa, as the gateway's check sees it."""

    @pytest.fixture
    def check(self, opa_url):
        opa = OpaClient(opa_url)
        yield PolicyCheck(opa)
        opa.close()

    @pytest.mark.parametrize(
        ("tool_name", "task"),
        [
            ("get_customer", "account_inquiry"),
            ("get_accounts", "account_inquiry"),
            ("get_transactions", "account_inquiry"),
            ("get_accounts", "refund_request"),
            ("issue_refund", "refund_request"),
            ("get_customer", "profile_update"),
            ("update_address", "profile_update"),
            ("get_accounts", "dispute"),
            ("close_dispute", "dispute"),
            ("freeze_account", "dispute"),
        ],
    )
    def test_vera_may_use_her_tools_for_the_tasks_that_allow_them(
        self, check, tool_name, task
    ):
        arguments = refund_arguments() if tool_name == "issue_refund" else None

        finding = check.evaluate(context(tool_name, task, arguments), [])

        assert not finding.objects
        assert finding.policy_version == BUNDLE_VERSION

    @pytest.mark.parametrize(
        ("tool_name", "task", "summary"),
        [
            (
                "issue_refund",
                "dispute",
                "issue_refund is not allowed for dispute tasks.",
            ),
            (
                "issue_refund",
                "account_inquiry",
                "issue_refund is not allowed for account_inquiry tasks.",
            ),
            (
                "freeze_account",
                "account_inquiry",
                "freeze_account is not allowed for account_inquiry tasks.",
            ),
            (
                "update_address",
                "refund_request",
                "update_address is not allowed for refund_request tasks.",
            ),
            (
                "reset_credentials",
                "admin_maintenance",
                "Vera is not allowed to use reset_credentials.",
            ),
        ],
    )
    def test_any_other_tool_or_task_is_blocked(self, check, tool_name, task, summary):
        arguments = refund_arguments() if tool_name == "issue_refund" else None

        finding = check.evaluate(context(tool_name, task, arguments), [])

        assert finding.decision is Decision.BLOCK
        assert finding.reasons == (ReasonCode.TOOL_NOT_ALLOWED,)
        assert finding.summary == summary

    def test_a_bulk_export_is_denied_first_of_all(self, check):
        finding = check.evaluate(context("export_customers", arguments={}), [])

        assert finding.decision is Decision.BLOCK
        assert finding.reasons == (ReasonCode.POLICY_DENY, ReasonCode.TOOL_NOT_ALLOWED)
        assert finding.summary == BULK["message"]
        assert finding.details["matched_rules"] == [
            "bulk_export",
            "tool_not_allowed_for_agent",
            "tool_not_allowed_for_task",
        ]

    @pytest.mark.parametrize(
        ("amount", "decision", "reasons"),
        [
            ("200.00", None, ()),
            ("200.01", Decision.HUMAN_REVIEW, (ReasonCode.REFUND_OVER_LIMIT,)),
            ("5000.00", Decision.HUMAN_REVIEW, (ReasonCode.REFUND_OVER_LIMIT,)),
            ("5000.01", Decision.BLOCK, (ReasonCode.REFUND_OVER_LIMIT,)),
            ("0.00", Decision.BLOCK, (ReasonCode.INVALID_ARGUMENTS,)),
            ("-50.00", Decision.BLOCK, (ReasonCode.INVALID_ARGUMENTS,)),
            ("120.505", Decision.BLOCK, (ReasonCode.INVALID_ARGUMENTS,)),
            (120, Decision.BLOCK, (ReasonCode.INVALID_ARGUMENTS,)),
        ],
    )
    def test_refund_amounts_are_checked_at_their_boundaries(
        self, check, amount, decision, reasons
    ):
        refund = context("issue_refund", "refund_request", refund_arguments(amount))

        finding = check.evaluate(refund, [])

        assert finding.decision is decision
        assert finding.reasons == reasons


class TestThroughTheGateway:
    @pytest.fixture
    def opa_gateway(self, make_gateway, opa_url):
        return make_gateway(policy=OpaClient(opa_url))

    def test_a_blocked_tool_never_reaches_the_bank_and_the_rules_are_audited(
        self, opa_gateway, evaluate, action, session_token, bank, audit
    ):
        body = action(tool_name="export_customers", arguments={}, provenance_labels={})

        decision = evaluate(body, client=opa_gateway).json()["decision"]

        assert decision["decision"] == "BLOCK"
        assert decision["reason_codes"] == ["POLICY_DENY", "TOOL_NOT_ALLOWED"]
        assert decision["policy_version"] == BUNDLE_VERSION
        assert bank.calls == []
        assert bank.lookups == []
        decided = audit.for_correlation(body["correlation_id"])[1]
        assert decided.policy_version == BUNDLE_VERSION
        (policy_check,) = [
            c for c in decided.payload["checks"] if c["check"] == "bank_policy"
        ]
        assert policy_check["details"]["matched_rules"] == [
            "bulk_export",
            "tool_not_allowed_for_agent",
            "tool_not_allowed_for_task",
        ]

    def test_an_allowed_action_records_the_policy_it_was_judged_against(
        self, opa_gateway, evaluate, action, audit
    ):
        body = action()

        outcome = evaluate(body, client=opa_gateway).json()

        assert outcome["decision"]["decision"] == "ALLOW"
        assert outcome["decision"]["policy_version"] == BUNDLE_VERSION
        assert outcome["execution"]["status"] == "succeeded"
        decided = audit.for_correlation(body["correlation_id"])[1]
        assert decided.policy_version == BUNDLE_VERSION

    def test_an_account_can_be_frozen_during_a_dispute(
        self, opa_gateway, evaluate, action, session_token, bank_store
    ):
        body = action(
            task_type="dispute",
            tool_name="freeze_account",
            arguments={"account_id": "ACC-00000123", "reason": "Suspected fraud"},
            provenance_labels={
                "account_id": "trusted_user_input",
                "reason": "trusted_user_input",
            },
        )

        outcome = evaluate(
            body, session=session_token(task_type="dispute"), client=opa_gateway
        ).json()

        assert outcome["decision"]["decision"] == "ALLOW"
        assert outcome["execution"]["result"]["status"] == "frozen"

    def test_an_unreachable_policy_fails_closed_and_logs_the_fault(
        self, make_gateway, evaluate, refund, refund_session, bank, caplog
    ):
        gateway = make_gateway(
            policy=OpaClient("http://127.0.0.1:9", timeout_seconds=0.5)
        )

        with caplog.at_level(logging.ERROR, logger="sentinel_gateway.orchestrator"):
            decision = evaluate(
                refund(), session=refund_session, client=gateway
            ).json()["decision"]

        assert decision["decision"] == "BLOCK"
        assert decision["reason_codes"] == ["DEPENDENCY_UNAVAILABLE"]
        assert decision["policy_version"] is None
        assert bank.calls == []
        assert bank.lookups == []
        assert "check bank_policy failed" in caplog.text
        assert gateway.get("/readyz").status_code == 503
        assert gateway.get("/readyz").json()["policy"] == "unavailable"
