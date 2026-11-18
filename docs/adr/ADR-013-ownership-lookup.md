# ADR-013: The gateway checks record ownership with the bank

| | |
|---|---|
| Status | Accepted |
| Date | 2026-11-18 |
| Deciders | Product Owner, Scrum Master, Code Owners |
| Requirements | FR-02, FR-03, FR-09; NFR-01, NFR-02, NFR-03 |
| Stories | US-01 (US-01.1), and later US-02a, US-02b |

## Context

US-01 must keep Vera inside the signed-in customer's data (UC-04). ADR-012 binds every action to a verified session, so the gateway knows the customer. Checking a `customer_id` argument against it is simple.

Most high-impact tools name other records instead: `issue_refund` takes an account and a purchase, `close_dispute` a dispute, `freeze_account` an account. Only the bank knows who owns `ACC-99000017`. Without that knowledge the gateway would allow a refund into another customer's account, which is the attack in UC-02.

## Decision

- The bank answers `POST /v1/internal/owners` with the owning customer of each account, transaction or dispute it is asked about, or null for a record it does not have. One lookup covers up to 100 records.
- The lookup needs an execution token issued for the name `resolve_owners`, bound to the action's correlation ID and customer, used once. Only the gateway can sign one, so Vera cannot call it. It is not in the tool catalogue.
- The gateway's `customer_scope` check finds every customer, account, transaction and dispute ID among the argument values, whatever the argument is called and however deeply it is nested. Customer IDs are compared with the session. The rest are looked up in one call.
- A record owned by another customer, or unknown to the bank, blocks the action with `OUTSIDE_CUSTOMER_SCOPE`. A lookup that fails blocks it with `DEPENDENCY_UNAVAILABLE`.
- The lookup is skipped when the action names only customer IDs, and when an earlier check has already blocked the action.
- The request and answer formats live in `sentinel_contracts.ownership`, shared by both services.

## Alternatives considered

| Alternative | Outcome |
|---|---|
| Check only `customer_id` arguments in Sprint 1 and leave the rest to OPA in US-02a | Enough to pass AT-02, but a refund into an attacker's account would be allowed for a whole sprint. Rejected. |
| Give the gateway a copy of the bank's ownership data | Rejected. The copy goes stale as soon as the bank changes, for example when a refund creates a new transaction, and the bank stops being the only source of truth. |
| Call the bank's `get_accounts` and `get_transactions` tools for the session's customer | Rejected. It mixes gateway lookups with agent tool calls in the bank's records, and `get_transactions` returns at most 100 recent transactions, so an older purchase could not be checked. |
| Let the bank reject a call for another customer's records | Rejected. The bank does not know which customer the session belongs to, and ADR-001 puts that decision in the gateway, before anything reaches the bank. |
| Match IDs by argument name, such as `account_id` | Rejected. A new tool with an argument called `target_account` would slip through. A test at the repository root fails if a bank tool ever takes an ID format the check does not know. |

## Consequences

What we gain:

- A refund to another customer's account, or of another customer's purchase, is blocked in Sprint 1, before the data-origin checks of US-02b exist.
- The bank stays the only source of truth for ownership.

What it costs:

- Actions that name accounts, transactions or disputes make one extra call to the bank before they are decided. It is a single in-memory lookup, well inside the 300 ms target of NFR-02; US-27 measures it.
- If the bank is down, those actions are blocked rather than allowed. Lookups by customer ID still work.
- The bank now has an endpoint that answers who owns what. It is protected by the same signed, single-use tokens as the tools, and the NetworkPolicy in US-23 will limit who can reach the bank at all.
