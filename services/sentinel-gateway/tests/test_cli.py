"""The command line: session tokens for local tests, and new keys."""

import pytest

from sentinel_contracts import load_key, verify_session_token
from sentinel_gateway.cli import main

SESSION_KEY = "session-key-for-cli-tests-0123456789abcdef"


@pytest.fixture
def session_key(monkeypatch):
    monkeypatch.setenv("SESSION_TOKEN_KEY", SESSION_KEY)


def test_issue_session_prints_a_token_the_gateway_accepts(session_key, capsys):
    code = main(
        [
            "issue-session",
            "--customer",
            "CUS-000123",
            "--task",
            "refund_request",
            "--session",
            "SES-00000042",
        ]
    )

    out, err = capsys.readouterr()
    claims = verify_session_token(out.strip(), key=load_key(SESSION_KEY))
    assert code == 0
    assert claims.customer_id == "CUS-000123"
    assert claims.session_id == "SES-00000042"
    assert claims.agent_id == "AGT-001"
    assert claims.task_type == "refund_request"
    assert claims.expires_at - claims.issued_at == 30 * 60
    assert "SES-00000042" in err


def test_issue_session_makes_up_a_session_id_when_none_is_given(session_key, capsys):
    main(
        [
            "issue-session",
            "--customer",
            "CUS-000123",
            "--task",
            "dispute",
            "--minutes",
            "5",
        ]
    )

    claims = verify_session_token(
        capsys.readouterr().out.strip(), key=load_key(SESSION_KEY)
    )
    assert claims.session_id.startswith("SES-")
    assert claims.expires_at - claims.issued_at == 300


@pytest.mark.parametrize(
    "extra",
    [
        ["--customer", "123"],
        ["--agent", "vera"],
        ["--minutes", "0"],
        ["--minutes", "241"],
    ],
)
def test_issue_session_refuses_bad_values(session_key, capsys, extra):
    args = ["issue-session", "--customer", "CUS-000123", "--task", "dispute", *extra]

    assert main(args) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert "Could not issue" in err


def test_issue_session_needs_the_session_key(monkeypatch, capsys):
    monkeypatch.delenv("SESSION_TOKEN_KEY", raising=False)

    assert main(["issue-session", "--customer", "CUS-000123", "--task", "dispute"]) == 2
    assert "SESSION_TOKEN_KEY" in capsys.readouterr().err


def test_new_key_prints_a_long_random_key(capsys):
    main(["new-key"])
    first = capsys.readouterr().out.strip()
    main(["new-key"])
    second = capsys.readouterr().out.strip()

    assert len(first) >= 48
    assert first != second
    load_key(first)
