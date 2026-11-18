"""The same correlation ID always gets the same decision, and the action runs at most once (US-18.5)."""

import threading
import time

import pytest

from sentinel_contracts import ExecutionResult


def test_a_repeated_refund_returns_the_same_outcome_and_pays_once(
    evaluate, refund, refund_session, bank, refunds_for, audit
):
    body = refund()
    first = evaluate(body, session=refund_session)
    second = evaluate(body, session=refund_session)

    assert first.status_code == second.status_code == 200
    assert second.json() == first.json()
    assert second.headers["X-Idempotent-Replay"] == "true"
    assert "X-Idempotent-Replay" not in first.headers
    assert len(bank.calls) == 1
    assert len(refunds_for("TXN-0000004568")) == 1
    assert len(audit.for_correlation(body["correlation_id"])) == 3


def test_a_repeated_block_returns_the_same_block(evaluate, action, bank):
    body = action(tool_name="wire_transfer", arguments={}, provenance_labels={})
    first = evaluate(body)
    second = evaluate(body)

    assert second.json() == first.json()
    assert second.json()["decision"]["decision"] == "BLOCK"
    assert second.headers["X-Idempotent-Replay"] == "true"
    assert bank.calls == []


def test_a_repeat_after_the_bank_failed_does_not_try_again(
    make_gateway, evaluate, action, settings, clock
):
    calls = []

    class FailingBank:
        def post(self, *args, **kwargs):
            calls.append(args)
            raise RuntimeError("connection pool exploded")

        def close(self):
            pass

    gateway = make_gateway(bank_client=FailingBank())
    body = action()
    first = evaluate(body, client=gateway)
    second = evaluate(body, client=gateway)

    execution = first.json()["execution"]
    assert execution["status"] == "failed"
    assert execution["error"]["code"] == "gateway_error"
    assert second.json() == first.json()
    assert len(calls) == 1


@pytest.mark.parametrize(
    "change",
    [
        pytest.param(
            {"arguments": {"customer_id": "CUS-000123", "limit": 3}}, id="arguments"
        ),
        pytest.param({"tool_name": "get_customer"}, id="tool"),
    ],
)
def test_a_different_request_with_a_used_correlation_id_is_refused(
    evaluate, action, bank, change
):
    body = action()
    evaluate(body)

    response = evaluate({**body, **change})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "correlation_id_conflict"
    assert len(bank.calls) == 1


def test_the_same_body_with_another_session_token_is_refused(
    evaluate, action, session_token, bank
):
    body = action()
    evaluate(body)

    response = evaluate(body, session=session_token())

    assert response.status_code == 200
    assert response.headers["X-Idempotent-Replay"] == "true"
    other_session = session_token(channel="mobile_app")
    assert evaluate(body, session=other_session).status_code == 409
    assert len(bank.calls) == 1


def test_another_agent_cannot_read_a_stored_outcome(
    evaluate, action, session_token, bank
):
    body = action()
    stored = evaluate(body)
    assert stored.json()["execution"]["status"] == "succeeded"

    response = evaluate(
        body, agent="AGT-002", session=session_token(agent_id="AGT-002")
    )

    assert response.status_code == 409
    assert "result" not in response.text
    assert len(bank.calls) == 1


def test_identical_requests_at_the_same_moment_run_once(
    make_gateway, evaluate, refund, refund_session, bank, refunds_for
):
    entered = threading.Event()

    class SlowBank:
        """Holds the first call open so the second request arrives while it runs."""

        def post(self, *args, **kwargs):
            entered.set()
            time.sleep(0.2)
            return bank.post(*args, **kwargs)

        def close(self):
            pass

    gateway = make_gateway(bank_client=SlowBank())
    body = refund()
    responses = []

    def send():
        responses.append(evaluate(body, session=refund_session, client=gateway))

    first = threading.Thread(target=send)
    first.start()
    assert entered.wait(timeout=5)
    send()
    first.join(timeout=5)

    assert [r.status_code for r in responses] == [200, 200]
    assert responses[0].json() == responses[1].json()
    assert sorted(r.headers.get("X-Idempotent-Replay", "") for r in responses) == [
        "",
        "true",
    ]
    assert len(refunds_for("TXN-0000004568")) == 1


def test_an_outcome_is_still_returned_when_the_last_audit_record_fails(
    make_gateway, evaluate, action, bank
):
    class FlakyAudit:
        def __init__(self):
            self.events = []

        def record(self, event):
            if event.event_type == "action_executed":
                raise OSError("disk full")
            self.events.append(event)

    audit = FlakyAudit()
    gateway = make_gateway(audit=audit)
    body = action()

    response = evaluate(body, client=gateway)

    assert response.status_code == 200
    ExecutionResult.model_validate(response.json()["execution"])
    assert [e.event_type for e in audit.events] == ["action_received", "decision_made"]
    assert evaluate(body, client=gateway).headers["X-Idempotent-Replay"] == "true"
    assert len(bank.calls) == 1


@pytest.mark.parametrize("failing_event", ["action_received", "decision_made"])
def test_nothing_runs_when_the_decision_cannot_be_audited(
    make_gateway, evaluate, action, bank, failing_event
):
    class BrokenAudit:
        fail = True

        def record(self, event):
            if self.fail and event.event_type == failing_event:
                raise ConnectionError("audit service down")

    audit = BrokenAudit()
    gateway = make_gateway(audit=audit)
    body = action()

    response = evaluate(body, client=gateway)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "audit_unavailable"
    assert bank.calls == []

    audit.fail = False
    retry = evaluate(body, client=gateway)
    assert retry.json()["decision"]["decision"] == "ALLOW"
    assert "X-Idempotent-Replay" not in retry.headers
    assert len(bank.calls) == 1
