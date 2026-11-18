"""The scenario runner command (US-17.3)."""

import functools

import httpx2
import pytest

from banking_agent import cli
from banking_agent.gateway import GatewayClient
from sentinel_contracts import Decision

ENV = {
    "GATEWAY_URL": "http://gateway.test",
    "VERA_AGENT_KEY": "vera-agent-key-0123456789abcdef0123456",
    "SESSION_TOKEN_KEY": "session-key-for-cli-tests-0123456789abcdef",
}


@pytest.fixture
def runner(monkeypatch, fake_gateway):
    """The CLI with its environment set and its gateway replaced by the fake one."""
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)
    transport = httpx2.MockTransport(fake_gateway.handler)
    monkeypatch.setattr(
        cli,
        "GatewayClient",
        functools.partial(
            GatewayClient,
            client=httpx2.Client(transport=transport),
            sleep=lambda s: None,
        ),
    )
    return cli.main


def test_list_shows_every_scenario_and_its_status(capsys):
    assert cli.main(["list"]) == 0

    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 7
    assert lines[0].startswith("UC-01  active")
    assert "pending (US-03)" in lines[2]


def test_run_reports_each_scenario_and_passes_when_all_match(
    runner, fake_gateway, capsys
):
    fake_gateway.decisions["get_transactions"] = [Decision.BLOCK, Decision.ALLOW]

    assert runner(["run", "UC-04"]) == 0

    out = capsys.readouterr().out
    assert "UC-04 Deny cross-customer access: PASSED" in out
    assert "Customer: Fine, show me mine then." in out
    assert "get_transactions: BLOCK (OUTSIDE_CUSTOMER_SCOPE)" in out
    assert "Vera: Here are your 2 most recent transactions." in out
    assert out.rstrip().endswith("1 passed, 0 failed, 0 pending")


def test_a_failing_active_scenario_fails_the_run(runner, capsys):
    assert runner(["run", "UC-05"]) == 1

    out = capsys.readouterr().out
    assert "UC-05 Block bulk export: FAILED" in out
    assert "! turn 1, export_customers: expected BLOCK, got ALLOW" in out


def test_pending_scenarios_are_skipped_unless_asked_for(runner, fake_gateway, capsys):
    assert runner(["run", "UC-03"]) == 0
    assert (
        "UC-03 Hold high-value refund: PENDING, waits on US-03"
        in capsys.readouterr().out
    )
    assert fake_gateway.requests == []

    assert runner(["run", "UC-03", "--include-pending"]) == 0
    assert len(fake_gateway.requests) == 1


def test_run_needs_vera_settings_and_the_session_key(monkeypatch, capsys):
    monkeypatch.delenv("VERA_AGENT_KEY", raising=False)
    monkeypatch.setenv("SESSION_TOKEN_KEY", ENV["SESSION_TOKEN_KEY"])

    assert cli.main(["run"]) == 2
    assert "VERA_AGENT_KEY is not set" in capsys.readouterr().err

    monkeypatch.setenv("VERA_AGENT_KEY", ENV["VERA_AGENT_KEY"])
    monkeypatch.delenv("SESSION_TOKEN_KEY", raising=False)
    assert cli.main(["run"]) == 2
    assert "Cannot run the scenarios" in capsys.readouterr().err


def test_an_unknown_scenario_is_refused(capsys):
    assert cli.main(["run", "UC-99"]) == 2
    assert "Unknown scenario(s): UC-99" in capsys.readouterr().err
