"""Least privilege: the tool allowlist and the customer scope check (US-01.1, US-01.2)."""

import uuid
from datetime import UTC, datetime

import httpx2
import pytest

from sentinel_contracts import (
    Decision,
    OwnershipQuery,
    ProtectedActionRequest,
    ReasonCode,
    verify_token,
)
from sentinel_contracts.ownership import (
    MAX_OWNERSHIP_QUERY,
    OWNERSHIP_PATH,
    OWNERSHIP_TOOL,
)
from sentinel_gateway.bank import BankClient, BankLookupError, BankOwnershipLookup
from sentinel_gateway.checks import ActionContext, CheckRecord, Stage, objection
from sentinel_gateway.registry import AgentRegistry, ToolRegistry
from sentinel_gateway.scope import (
    CustomerScopeCheck,
    RecordKind,
    ToolAllowlistCheck,
    referenced_records,
)

RECEIVED = datetime(2027, 1, 15, 8, 0, tzinfo=UTC)
VERA = AgentRegistry.load().get("AGT-001")
TOOLS = ToolRegistry.load()
KEY = b"execution-key-for-scope-tests-0123456789"

OWNERS = {
    "ACC-00000123": "CUS-000123",
    "TXN-0000004568": "CUS-000123",
    "DSP-000001": "CUS-000123",
    "ACC-99000017": "CUS-990001",
    "TXN-0000004570": "CUS-000456",
}


class FakeOwnership:
    """Answers from OWNERS and remembers every lookup."""

    def __init__(self, owners=None, error=None):
        self.owners_by_id = OWNERS if owners is None else owners
        self.error = error
        self.asked = []

    def owners(self, request, identifiers):
        self.asked.append(sorted(identifiers))
        if self.error is not None:
            raise self.error
        return {i: self.owners_by_id.get(i) for i in identifiers}


def context(
    *, tool_name="get_transactions", arguments=None, task="account_inquiry", agent=VERA
):
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
        agent=agent,
        tool=TOOLS.get(tool_name),
        session=None,
        session_error=None,
        received_at=RECEIVED,
    )


def refund_arguments(account="ACC-00000123", transaction="TXN-0000004568"):
    return {
        "account_id": account,
        "amount": "120.00",
        "original_transaction_id": transaction,
        "reason": "Duplicate charge",
    }


class TestToolAllowlist:
    check = ToolAllowlistCheck()

    @pytest.mark.parametrize(
        ("tool_name", "task"),
        [
            ("get_transactions", "account_inquiry"),
            ("get_customer", "profile_update"),
            ("update_address", "profile_update"),
            ("issue_refund", "refund_request"),
            ("issue_refund", "dispute"),
            ("close_dispute", "dispute"),
        ],
    )
    def test_vera_may_use_her_tools_for_the_right_tasks(self, tool_name, task):
        finding = self.check.evaluate(context(tool_name=tool_name, task=task), [])

        assert not finding.objects

    @pytest.mark.parametrize(
        ("tool_name", "task", "for_agent", "for_task", "summary"),
        [
            (
                "export_customers",
                "admin_maintenance",
                False,
                True,
                "Vera is not allowed to use export_customers.",
            ),
            (
                "issue_refund",
                "account_inquiry",
                True,
                False,
                "issue_refund is not allowed for account_inquiry tasks.",
            ),
            (
                "freeze_account",
                "account_inquiry",
                False,
                False,
                (
                    "Vera is not allowed to use freeze_account, and freeze_account "
                    "is not allowed for account_inquiry tasks."
                ),
            ),
            (
                "get_accounts",
                "account_inquiry",
                False,
                True,
                "Vera is not allowed to use get_accounts.",
            ),
        ],
    )
    def test_any_other_tool_or_task_is_blocked(
        self, tool_name, task, for_agent, for_task, summary
    ):
        finding = self.check.evaluate(context(tool_name=tool_name, task=task), [])

        assert finding.decision is Decision.BLOCK
        assert finding.reasons == (ReasonCode.TOOL_NOT_ALLOWED,)
        assert finding.summary == summary
        assert finding.details == {
            "allowed_for_agent": for_agent,
            "allowed_for_task": for_task,
        }

    def test_without_an_agent_or_tool_entry_nothing_is_allowed(self):
        finding = self.check.evaluate(
            context(tool_name="wire_transfer", agent=None), []
        )

        assert finding.decision is Decision.BLOCK
        assert finding.summary.startswith("This agent is not allowed")


class TestCustomerScope:
    def test_the_customers_own_records_pass(self):
        ownership = FakeOwnership()
        check = CustomerScopeCheck(ownership)

        finding = check.evaluate(
            context(
                tool_name="issue_refund",
                arguments=refund_arguments(),
                task="refund_request",
            ),
            [],
        )

        assert not finding.objects
        assert ownership.asked == [["ACC-00000123", "TXN-0000004568"]]

    def test_another_customers_id_is_blocked_without_asking_the_bank(self):
        ownership = FakeOwnership()

        finding = CustomerScopeCheck(ownership).evaluate(
            context(arguments={"customer_id": "CUS-000456", "limit": 5}), []
        )

        assert finding.decision is Decision.BLOCK
        assert finding.reasons == (ReasonCode.OUTSIDE_CUSTOMER_SCOPE,)
        assert "CUS-000456" in finding.summary
        assert finding.details == {
            "outside_scope": {"CUS-000456": "CUS-000456"},
            "unknown": [],
        }
        assert ownership.asked == []

    @pytest.mark.parametrize(
        ("arguments", "outside", "unknown"),
        [
            pytest.param(
                refund_arguments(account="ACC-99000017"),
                {"ACC-99000017": "CUS-990001"},
                [],
                id="refund to another customer's account",
            ),
            pytest.param(
                refund_arguments(transaction="TXN-0000004570"),
                {"TXN-0000004570": "CUS-000456"},
                [],
                id="refund of another customer's purchase",
            ),
            pytest.param(
                refund_arguments(account="ACC-12345678"),
                {},
                ["ACC-12345678"],
                id="account the bank does not have",
            ),
        ],
    )
    def test_records_owned_by_someone_else_or_nobody_are_blocked(
        self, arguments, outside, unknown
    ):
        finding = CustomerScopeCheck(FakeOwnership()).evaluate(
            context(
                tool_name="issue_refund", arguments=arguments, task="refund_request"
            ),
            [],
        )

        assert finding.decision is Decision.BLOCK
        assert finding.reasons == (ReasonCode.OUTSIDE_CUSTOMER_SCOPE,)
        assert finding.details == {"outside_scope": outside, "unknown": unknown}

    def test_ids_are_found_wherever_they_appear_in_the_arguments(self):
        arguments = {
            "note": "Avery asked about ACC-99000017",
            "targets": [{"account": "ACC-99000017"}, ["DSP-000001"]],
            "by_id": {"CUS-000456": True},
        }

        found = referenced_records(arguments)

        assert found == {
            RecordKind.ACCOUNT: {"ACC-99000017"},
            RecordKind.DISPUTE: {"DSP-000001"},
            RecordKind.CUSTOMER: {"CUS-000456"},
        }

    def test_free_text_and_near_misses_are_not_ids(self):
        assert referenced_records({"reason": "refund ACC-99000017 please"}) == {}
        assert referenced_records({"account_id": "ACC-99000017\n"}) == {}
        assert referenced_records({"account_id": "acc-99000017"}) == {}

    def test_the_summary_lists_a_few_records_and_counts_the_rest(self):
        accounts = [f"ACC-9900{n:04d}" for n in range(5)]

        finding = CustomerScopeCheck(FakeOwnership(owners={})).evaluate(
            context(arguments={"customer_id": "CUS-000123", "accounts": accounts}), []
        )

        assert "ACC-99000000, ACC-99000001, ACC-99000002 and 2 more" in finding.summary
        assert len(finding.summary) <= 300

    def test_too_many_records_to_check_is_blocked(self):
        accounts = [f"ACC-{n:08d}" for n in range(MAX_OWNERSHIP_QUERY + 1)]
        ownership = FakeOwnership()

        finding = CustomerScopeCheck(ownership).evaluate(
            context(arguments={"accounts": accounts}), []
        )

        assert finding.reasons == (ReasonCode.INVALID_ARGUMENTS,)
        assert ownership.asked == []

    def test_a_failed_lookup_raises_so_the_action_fails_closed(self):
        check = CustomerScopeCheck(FakeOwnership(error=BankLookupError("down")))

        with pytest.raises(BankLookupError):
            check.evaluate(
                context(
                    tool_name="issue_refund",
                    arguments=refund_arguments(),
                    task="refund_request",
                ),
                [],
            )

    def test_the_bank_is_not_asked_once_the_action_is_already_blocked(self):
        ownership = FakeOwnership()
        blocked = CheckRecord(
            "tool_allowlist",
            Stage.HARD_RULE,
            objection(Decision.BLOCK, ReasonCode.TOOL_NOT_ALLOWED, summary="No."),
        )

        finding = CustomerScopeCheck(ownership).evaluate(
            context(
                tool_name="issue_refund",
                arguments=refund_arguments(),
                task="account_inquiry",
            ),
            [blocked],
        )

        assert not finding.objects
        assert finding.details == {
            "ownership_not_checked": ["ACC-00000123", "TXN-0000004568"]
        }
        assert ownership.asked == []


class TestBankOwnershipLookup:
    def lookup(self, handler):
        client = BankClient(
            "http://bank.test",
            client=httpx2.Client(transport=httpx2.MockTransport(handler)),
        )
        return BankOwnershipLookup(
            client, key=KEY, audience="demo-bank-api", clock=lambda: 1_800_000_000.0
        )

    def test_the_lookup_sends_a_token_for_exactly_this_query(self):
        seen = {}

        def handler(request):
            seen["path"] = request.url.path
            seen["body"] = request.content
            seen["token"] = request.headers["X-Execution-Token"]
            return httpx2.Response(
                200, json={"owners": {"ACC-00000123": "CUS-000123", "DSP-000001": None}}
            )

        request = context().request
        owners = self.lookup(handler).owners(request, {"DSP-000001", "ACC-00000123"})

        assert owners == {"ACC-00000123": "CUS-000123", "DSP-000001": None}
        assert seen["path"] == OWNERSHIP_PATH
        assert seen["body"] == b'{"identifiers":["ACC-00000123","DSP-000001"]}'
        claims = verify_token(
            seen["token"],
            key=KEY,
            audience="demo-bank-api",
            tool_name=OWNERSHIP_TOOL,
            arguments=OwnershipQuery(
                identifiers=["ACC-00000123", "DSP-000001"]
            ).model_dump(mode="json"),
            now=1_800_000_000.0,
        )
        assert claims.correlation_id == request.correlation_id
        assert claims.customer_scope == "CUS-000123"

    @pytest.mark.parametrize(
        "response",
        [
            httpx2.Response(
                403, json={"error": {"code": "token_replayed", "message": "used"}}
            ),
            httpx2.Response(500, text="boom"),
            httpx2.Response(200, text="not json"),
            httpx2.Response(200, json={"owners": {"ACC-00000123": "Avery"}}),
            httpx2.Response(200, json={"owners": {}}),
        ],
    )
    def test_any_answer_but_a_complete_one_is_a_lookup_error(self, response):
        with pytest.raises(BankLookupError):
            self.lookup(lambda request: response).owners(
                context().request, {"ACC-00000123"}
            )

    def test_an_unreachable_bank_is_a_lookup_error(self):
        def handler(request):
            raise httpx2.ConnectError("refused")

        with pytest.raises(BankLookupError, match="could not be reached"):
            self.lookup(handler).owners(context().request, {"ACC-00000123"})


class TestThroughTheGateway:
    def test_a_refund_to_an_attackers_account_never_reaches_the_bank(
        self, evaluate, refund, refund_session, bank, audit, refunds_for
    ):
        body = refund(arguments=refund_arguments(account="ACC-99000017"))

        decision = evaluate(body, session=refund_session).json()["decision"]

        assert decision["decision"] == "BLOCK"
        assert decision["reason_codes"] == ["OUTSIDE_CUSTOMER_SCOPE"]
        assert "CUS-990001" not in decision["summary"]
        assert bank.calls == []
        assert len(bank.lookups) == 1
        assert refunds_for("TXN-0000004568") == []
        checks = audit.for_correlation(body["correlation_id"])[1].payload["checks"]
        assert checks[-1]["details"]["outside_scope"] == {"ACC-99000017": "CUS-990001"}

    def test_a_tool_vera_may_not_use_is_blocked_before_any_lookup(
        self, evaluate, action, session_token, bank
    ):
        body = action(
            task_type="admin_maintenance",
            tool_name="freeze_account",
            arguments={"account_id": "ACC-99000017", "reason": "Suspicious activity"},
            provenance_labels={},
        )

        decision = evaluate(
            body, session=session_token(task_type="admin_maintenance")
        ).json()["decision"]

        assert decision["decision"] == "BLOCK"
        assert decision["reason_codes"] == ["TOOL_NOT_ALLOWED"]
        assert bank.calls == []
        assert bank.lookups == []

    def test_a_tool_outside_the_task_is_blocked(self, evaluate, refund, bank):
        decision = evaluate(refund(task_type="account_inquiry")).json()["decision"]

        assert decision["reason_codes"] == ["TOOL_NOT_ALLOWED"]
        assert bank.calls == []
        assert bank.lookups == []

    def test_an_unreachable_ownership_lookup_blocks_the_action(
        self, make_gateway, evaluate, refund, refund_session
    ):
        class DownBank:
            def post(self, *args, **kwargs):
                raise httpx2.ConnectError("refused")

            def close(self):
                pass

        gateway = make_gateway(bank_client=DownBank())

        decision = evaluate(refund(), session=refund_session, client=gateway).json()[
            "decision"
        ]

        assert decision["decision"] == "BLOCK"
        assert decision["reason_codes"] == ["DEPENDENCY_UNAVAILABLE"]
        assert "customer_scope" in decision["summary"]
