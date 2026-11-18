"""Sprint 1 goal (M2): one ALLOW and one BLOCK flow run end to end through the gateway
and are fully audited in the hash-linked trail (US-17, US-18, US-01, US-19).

Needs PostgreSQL (AUDIT_TEST_DATABASE_URL); skipped without it. The Docker Compose
job in CI runs the same flow against the real containers.
"""

from banking_agent.scenarios import load_scenarios, run_scenario
from sentinel_audit.completeness import check_completeness
from sentinel_audit.store import AuditStore
from sentinel_audit.verify import verify_chain

SCENARIOS = {scenario.id: scenario for scenario in load_scenarios()}


def test_allow_and_block_flows_are_fully_audited_in_the_chain(
    make_stack, audit_database
):
    store = AuditStore.connect(audit_database, wait=True)
    try:
        stack = make_stack(audit=store)
        vera, identity = stack.vera()

        allowed = run_scenario(SCENARIOS["UC-01"], vera, identity)
        blocked = run_scenario(SCENARIOS["UC-04"], vera, identity)

        assert allowed.status == blocked.status == "passed"
        events = list(store.events())
        correlation_ids = (
            allowed.conversation.correlation_ids()
            + blocked.conversation.correlation_ids()
        )
        assert verify_chain(events).intact
        report = check_completeness(events, expected=correlation_ids)
        assert report.ok, report.incomplete
        assert report.actions == 4
        decisions = [e.decision for e in events if e.event_type == "decision_made"]
        assert decisions == ["ALLOW", "ALLOW", "BLOCK", "ALLOW"]
    finally:
        store.close()
