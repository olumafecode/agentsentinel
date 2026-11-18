"""The standard set of checks and the order they run in."""

from sentinel_gateway.checks import Stage
from sentinel_gateway.orchestrator import Orchestrator
from sentinel_gateway.pipeline import default_checks


class NoLookups:
    def owners(self, request, identifiers):
        raise AssertionError("not expected in this test")


def test_the_gateway_runs_context_checks_then_least_privilege_rules():
    checks = Orchestrator(default_checks(ownership=NoLookups())).checks

    assert [(check.name, check.stage) for check in checks] == [
        ("context_binding", Stage.CONTEXT),
        ("agent_status", Stage.CONTEXT),
        ("request_freshness", Stage.CONTEXT),
        ("known_tool", Stage.CONTEXT),
        ("tool_allowlist", Stage.HARD_RULE),
        ("customer_scope", Stage.HARD_RULE),
    ]
