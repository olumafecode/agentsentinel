"""The checks the gateway runs on every action (ADR-012).

The orchestrator sorts them by stage, so the order here matters only within a stage.
The bank policy runs before the customer scope check: when the policy blocks an
action, the scope check does not ask the bank who owns its records. Each story that
adds a rule adds it here, with any client it needs passed in as an argument.
"""

from sentinel_gateway.checks import (
    AgentStatusCheck,
    Check,
    ContextBindingCheck,
    KnownToolCheck,
    RequestFreshnessCheck,
)
from sentinel_gateway.policy import PolicyCheck, PolicyEngine
from sentinel_gateway.scope import CustomerScopeCheck, OwnershipLookup


def default_checks(*, ownership: OwnershipLookup, policy: PolicyEngine) -> list[Check]:
    """Every check, given the clients the checks need."""
    return [
        # CONTEXT (US-18)
        ContextBindingCheck(),
        AgentStatusCheck(),
        RequestFreshnessCheck(),
        KnownToolCheck(),
        # HARD_RULE: bank policy in OPA (US-02a), then customer scope (US-01)
        PolicyCheck(policy),
        CustomerScopeCheck(ownership),
    ]
