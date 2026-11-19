
# Sprint 1 weekly scrums and refinement

Sprint 1 runs 16 to 29 November 2026. Record what was actually said and the real date of each meeting.

## Weekly scrum

**Date:** 18 November 2026  
**Attendees:** Olusanya Mafe / Siyabonga Jali  

| Person | Finished since the sprint started | Doing next | Blockers |
|---|---|---|---|
| Olusanya Mafe | Shared contracts and execution tokens (US-18.1, PR #121); demo bank API (US-16, PR #122); gateway evaluate endpoint, decision orchestrator, tokens and idempotency (US-18.2 to US-18.6, PR #123); customer scope and tool allowlist with AT-01 and AT-02 (US-01, PR #125); Vera in scripted mode, hash-linked audit trail and Docker Compose stack (US-17, US-19, US-20, PR #126); OPA health check fix (PR #131) | Record the Sprint 1 demo; draft the review and retrospective notes | Resolved: the Images workflow failed on `main` because OPA's health check needed `wget`; fixed in PR #131 |
| Siyabonga Jali | Reviewed and merged PR #126 | Watch the demo and accept or return each story |  |

Board updated during the meeting: [yes / no]  
Actions (owner, due): no

- Olusanya Mafe: record the Sprint 1 demo and share the link, by 11/20/2026
- Siyabonga Jali: accept or return each story after the demo and close the accepted ones, by 11/20/2026
- Both: close the Dependabot pull requests #124 and #127 to #130, [if not done already]

No second weekly scrum was held: all Sprint 1 work was merged by 18 November, and the review was held on 19 November 2026.

# Backlog refinement for Sprint 2

**Date:** 19 November 2026  
**Attendees:** Olusanya Mafe / Siyabonga Jali

Sprint 2 checked against the Definition of Ready:

| Story | Points | Ready? | Notes or re-estimate |
|---|---|---|---|
| US-02a Block unsafe tool calls with versioned OPA policy | 5 | Yes | OPA already runs in the Compose stack (US-20), and the OPA check goes into the gateway's existing hard-rule stage. The task-to-tool table in the gateway's `tools.json` moves into Rego, so the Product Owner confirms it first. A check that fails already gives BLOCK with DEPENDENCY_UNAVAILABLE, which covers most of AT-12. Do it first, because US-02b's rule runs through the same OPA client |
| US-02b Block refunds whose details came from untrusted content | 8 | Yes | At the 8-point limit. Provenance labels, the UNTRUSTED_ORIGIN reason code and the audit column for the labels already exist from Sprint 1. UC-02 is already blocked by the ownership lookup, because the attacker's account belongs to another customer, so AT-06 also needs a case the scope check cannot catch: an amount taken from the email and paid into the customer's own account. Needs US-02a's OPA client |
| US-21 Generate the labelled synthetic action dataset | 5 | Yes | The labelling rules and limits were confirmed in Sprint 0 (US-15). The generator reads the limits from the OPA data file written in US-02a, so the labels and the live policy cannot drift apart. The Product Owner checks a 50-event sample by hand. Must finish in week 1, because US-04 trains on it |
| US-04 Score suspicious actions and sequences | 8 | Yes | At the 8-point limit. Needs the frozen dataset from US-21. The risk engine is a new service, so it also needs a Dockerfile, health endpoints, a Compose health check and an entry in the Images workflow, as set up in US-20. If it runs over, split the gateway integration and velocity limits (task 4) into their own story. Turns on Vera's UC-06 scenario |
| US-06a Explain blocked and held decisions with policy citations | 8 | Yes | At the 8-point limit. The Product Owner writes the four policy documents with section IDs in week 1; nothing can be embedded until they exist. pgvector is already in the PostgreSQL image. The explanation service is a second new service. The LLM adapter needs a provider (ADR-007); CI and the recorded demo use the mock |

Order of work:

- Week 1: US-02a, US-21, the four policy documents (US-06a task 1) and the poisoned email and document fixtures (US-02b task 4).
- Week 2: the rest of US-02b, then US-04 and US-06a.
- As in Sprint 1, new contracts go into `libs/sentinel-contracts` before the services that use them: the `/score` and `/explain` requests and responses, and the explanation evidence record.

Decisions and changes to the backlog:

- All five stories meet the Definition of Ready. Estimates stand at 34 points.
- 34 points is 5 more than Sprint 1's 29. We are keeping it because all of Sprint 1 was merged in its first three days. If we are behind at the 9 December scrum, US-06a ships on the mock LLM provider and the live provider moves to Sprint 3.
- Vera's runtime sets the provenance labels by comparing each argument with what the customer typed. The planner never sets them, so injected text cannot relabel its own values. In Sprint 1 the scenario files declared the labels; from US-02b they keep them only as expected results. The gateway treats a sensitive argument with no label as untrusted, as the contract already says.
- A refund whose sensitive details came from untrusted content is blocked. HUMAN_REVIEW stays available as a setting. This matches dataset rule R4.
- If the risk engine cannot be reached, the gateway fails closed as it does for OPA: the action is blocked with DEPENDENCY_UNAVAILABLE.
- The explanation service uses [provider and model] through the ADR-007 adapter, with a spend cap of [amount] a month. The key is kept only in `.env`.
- The risk engine and the explanation service join the Compose stack job, which becomes a required check on `main` (Sprint 1 retrospective).

Actions (owner, due):

- Siyabonga Jali: confirm the task-to-tool table in `tools.json`, and whether Vera's allowed tools include `get_accounts`, before US-02a starts
- Siyabonga Jali: write the four policy documents with section IDs (AI Agent Access Policy, Customer Data Access Policy, Refund Authorization Policy, Incident Response Standard), by [end of week 1]
- Siyabonga Jali: check the 50-event sample from the US-21 generator by hand, by [end of week 1]
- Both: choose the LLM provider and spend cap for US-06a, by Sprint 2 planning
