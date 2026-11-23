"""The standard set of checks and the order they run in."""

from sentinel_gateway.checks import Stage
from sentinel_gateway.orchestrator import Orchestrator
from sentinel_gateway.pipeline import default_checks


class NoLookups:
    def owners(self, request, identifiers):
        raise AssertionError("not expected in this test")


class NoPolicy:
    def evaluate(self, document):
        raise AssertionError("not expected in this test")

    def ready(self):
        return True


def test_the_gateway_runs_context_checks_then_bank_policy_then_customer_scope():
    checks = Orchestrator(
        default_checks(ownership=NoLookups(), policy=NoPolicy())
    ).checks

    assert [(check.name, check.stage) for check in checks] == [
        ("context_binding", Stage.CONTEXT),
        ("agent_status", Stage.CONTEXT),
        ("request_freshness", Stage.CONTEXT),
        ("known_tool", Stage.CONTEXT),
        ("bank_policy", Stage.HARD_RULE),
        ("customer_scope", Stage.HARD_RULE),
    ]
