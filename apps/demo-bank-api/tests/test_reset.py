"""Reset returns the bank to its seeded state (US-16 criterion 3)."""

import dataclasses
import io
import json
import urllib.error

import pytest
from fastapi.testclient import TestClient

from demo_bank_api import cli
from demo_bank_api.main import create_app
from demo_bank_api.store import BankStore

ADMIN = {"X-Admin-Key": "admin-test-key-0123456789"}
REFUND = {
    "account_id": "ACC-00000123",
    "amount": "120.00",
    "original_transaction_id": "TXN-0000004568",
    "reason": "Item returned",
}


def test_reset_returns_the_bank_to_the_seeded_state(client, call, store):
    seeded = BankStore().checksum()
    assert call("issue_refund", REFUND).status_code == 200
    freeze = {"account_id": "ACC-00000456", "reason": "Lost card"}
    assert call("freeze_account", freeze).status_code == 200
    assert store.checksum() != seeded

    response = client.post("/admin/reset", headers=ADMIN)

    assert response.status_code == 200
    assert response.json() == {
        "status": "reset",
        "seed": store.seed,
        "checksum": seeded,
    }
    assert store.checksum() == seeded


def test_the_same_refund_works_again_after_a_reset(client, call):
    assert call("issue_refund", REFUND).status_code == 200
    assert call("issue_refund", REFUND).status_code == 409
    client.post("/admin/reset", headers=ADMIN)
    assert call("issue_refund", REFUND).status_code == 200


@pytest.mark.parametrize("headers", [{}, {"X-Admin-Key": "wrong-key-0123456789"}])
def test_reset_needs_the_admin_key(client, headers):
    response = client.post("/admin/reset", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "invalid_admin_key"


def test_reset_is_disabled_without_an_admin_key(settings, store, clock):
    app = create_app(
        dataclasses.replace(settings, admin_key=None), store=store, clock=clock
    )
    with TestClient(app) as client:
        response = client.post("/admin/reset", headers=ADMIN)
    assert response.status_code == 404


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_cli_reset_calls_the_running_bank(monkeypatch, capsys):
    sent = {}

    def fake_urlopen(request, timeout):
        sent["url"] = request.full_url
        sent["key"] = request.get_header("X-admin-key")
        sent["method"] = request.get_method()
        return FakeResponse(json.dumps({"status": "reset", "checksum": "abc"}).encode())

    monkeypatch.setenv("DEMO_ADMIN_KEY", "admin-test-key-0123456789")
    monkeypatch.setattr(cli.urllib.request, "urlopen", fake_urlopen)

    assert cli.main(["reset", "--url", "http://bank.test:8001/"]) == 0
    assert sent == {
        "url": "http://bank.test:8001/admin/reset",
        "key": "admin-test-key-0123456789",
        "method": "POST",
    }
    assert json.loads(capsys.readouterr().out)["status"] == "reset"


def test_cli_reset_only_accepts_web_addresses(monkeypatch, capsys):
    monkeypatch.setenv("DEMO_ADMIN_KEY", "admin-test-key-0123456789")
    assert cli.main(["reset", "--url", "file:///etc/passwd"]) == 2
    assert "http" in capsys.readouterr().err


def test_cli_reset_needs_the_admin_key(monkeypatch, capsys):
    monkeypatch.delenv("DEMO_ADMIN_KEY", raising=False)
    assert cli.main(["reset"]) == 2
    assert "DEMO_ADMIN_KEY" in capsys.readouterr().err


@pytest.mark.parametrize(
    "failure",
    [
        urllib.error.HTTPError(
            "http://bank.test", 403, "Forbidden", {}, io.BytesIO(b"{}")
        ),
        urllib.error.URLError("connection refused"),
    ],
)
def test_cli_reset_reports_failures(monkeypatch, capsys, failure):
    def fake_urlopen(request, timeout):
        raise failure

    monkeypatch.setenv("DEMO_ADMIN_KEY", "admin-test-key-0123456789")
    monkeypatch.setattr(cli.urllib.request, "urlopen", fake_urlopen)
    assert cli.main(["reset", "--url", "http://bank.test"]) == 1
    assert capsys.readouterr().err


def test_cli_seed_info_matches_the_seeded_checksum(capsys):
    assert cli.main(["seed-info"]) == 0
    info = json.loads(capsys.readouterr().out)
    assert info["checksum"] == BankStore().checksum()
    assert info["customers"] == 43
