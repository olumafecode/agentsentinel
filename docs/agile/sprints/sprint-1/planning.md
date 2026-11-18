# Sprint 1 planning

**Date:** 16 November 2026  
**Attendees:** Olusanya Mafe, Siyabonga Jali  
**Sprint dates:** Monday 16 November to Sunday 29 November 2026 (two weeks)  
**Sprint goal:** One ALLOW and one BLOCK flow run end to end through the gateway and are fully audited (milestone M2).  

What the goal means at the review on 29 November: `docker compose up` starts the demo bank API, the gateway and PostgreSQL. A lookup of Customer A's own transactions is allowed and returns data (AT-01). A lookup of Customer B's records from Customer A's session is blocked, and the bank API is never called (AT-02). Both decisions have a complete, hash-linked audit event.

Events: weekly scrums on Wednesday 18 and 25 November, backlog refinement on Thursday 19 November, review with recorded demo and retrospective on Sunday 29 November. Ceremony checklist: [#12](https://github.com/olumafecode/agentsentinel/issues/12).

## Capacity

| Person | Available days this sprint | Notes (holidays, exams, work travel) |
|---|---|---|
| Olusanya Mafe | 11 | Thanksgiving, 26 and 27 November |
| Siyabonga Jali | 11 | Thanksgiving, 26 and 27 November |

Previous sprint velocity: 15 points (Sprint 0, one week). Planned this sprint: 29 points.

Two weeks at the Sprint 0 pace, less the two holiday days, makes 29 points the most we can take. We check progress at the 25 November scrum.

## Part 1: what we will deliver (sprint backlog)

| Story | Points | Why now |
|---|---|---|
| [#24](https://github.com/olumafecode/agentsentinel/issues/24) US-18 Intercept every protected tool call at the gateway | 8 | The core of AgentSentinel and of the sprint goal; every later story builds on it (FR-01, FR-02, FR-08, FR-09) |
| [#22](https://github.com/olumafecode/agentsentinel/issues/22) US-16 Build the synthetic demo bank API | 3 | The gateway needs something to protect, and Vera needs tools to call (NFR-08, NFR-10) |
| [#27](https://github.com/olumafecode/agentsentinel/issues/27) US-20 Run the whole stack with one Docker Compose command | 3 | The goal must run in containers, and US-19 needs PostgreSQL (FR-19, NFR-10, NFR-14) |
| [#26](https://github.com/olumafecode/agentsentinel/issues/26) US-19 Write a hash-linked audit event for every decision | 5 | "Fully audited" is part of the goal (FR-13, NFR-06) |
| [#25](https://github.com/olumafecode/agentsentinel/issues/25) US-01 Keep Vera inside the current customer's data | 5 | Produces the ALLOW and BLOCK flows for the demo (AT-01, AT-02) |
| [#23](https://github.com/olumafecode/agentsentinel/issues/23) US-17 Run Vera in scripted mode through the gateway only | 5 | Drives the demo scenarios end to end, the same way every time (FR-01, NFR-14) |
| **Total** | **29** | |

Stories considered but not taken, and why:

- US-02a (OPA policy) and US-02b (untrusted origin): they plug into the gateway's decision step, so they follow US-18 in Sprint 2.
- US-21 (labelled dataset): not needed until the risk model in Sprint 2, and this sprint is already at capacity.

## Part 2: how we will deliver it (tasks and owners)

Tasks were created with `plan-sprint` on 16 November and are assigned on the board. The work runs in two tracks so neither person waits on the other: Olusanya builds the gateway and the demo bank (16 points), and Siyabonga builds the platform, the audit trail and Vera (13 points). US-18.1 comes first because every service exchanges those two messages.

| Story | Task | Owner | Week |
|---|---|---|---|
| US-18 | [#98](https://github.com/olumafecode/agentsentinel/issues/98) US-18.1 Define ProtectedActionRequest and GovernanceDecision contracts (Pydantic)  | Olusanya Mafe | 1 |
| US-18 | [#99](https://github.com/olumafecode/agentsentinel/issues/99) US-18.2 Build POST /v1/actions/evaluate with context binding from token and session claims | Olusanya Mafe | 1 |
| US-18 | [#100](https://github.com/olumafecode/agentsentinel/issues/100) US-18.3 Decision orchestrator with deny by default and the Appendix E precedence order | Olusanya Mafe | 1 |
| US-18 | [#101](https://github.com/olumafecode/agentsentinel/issues/101) US-18.4 Signed single-use execution token issued by the gateway and verified by the bank API | Olusanya Mafe | 2 |
| US-18 | [#102](https://github.com/olumafecode/agentsentinel/issues/102) US-18.5 Idempotent decisions by correlation ID | Olusanya Mafe | 2 |
| US-18 | [#103](https://github.com/olumafecode/agentsentinel/issues/103) US-18.6 Unit and contract tests, including a token replay attempt | Olusanya Mafe | 2 |
| US-16 | [#90](https://github.com/olumafecode/agentsentinel/issues/90) US-16.1 FastAPI service with tools: get_customer, get_transactions, update_address, issue_refund, close_dispute, export_customers, admin tools | Olusanya Mafe | 1 |
| US-16 | [#91](https://github.com/olumafecode/agentsentinel/issues/91) US-16.2 Seed generator with a fixed seed and a demo reset command | Olusanya Mafe | 1 |
| US-16 | [#92](https://github.com/olumafecode/agentsentinel/issues/92) US-16.3 Unit tests for each endpoint | Olusanya Mafe | 1 |
| US-16 | [#93](https://github.com/olumafecode/agentsentinel/issues/93) US-16.4 Dockerfile and health endpoint | Olusanya Mafe | 1 |
| US-20 | [#113](https://github.com/olumafecode/agentsentinel/issues/113) US-20.1 Dockerfiles: slim base image, non-root user, pinned versions | Siyabonga Jali | 1 |
| US-20 | [#114](https://github.com/olumafecode/agentsentinel/issues/114) US-20.2 docker-compose.yml with health checks and .env.example | Siyabonga Jali | 1 |
| US-20 | [#115](https://github.com/olumafecode/agentsentinel/issues/115) US-20.3 /healthz and /readyz on every service | Siyabonga Jali | 2 |
| US-20 | [#116](https://github.com/olumafecode/agentsentinel/issues/116) US-20.4 CI job: build images tagged with the commit SHA, scan with Trivy, push to GitHub Container Registry on main | Siyabonga Jali | 2 |
| US-19 | [#108](https://github.com/olumafecode/agentsentinel/issues/108) US-19.1 PostgreSQL schema and migrations for ToolCall and AuditEvent | Siyabonga Jali | 1 |
| US-19 | [#109](https://github.com/olumafecode/agentsentinel/issues/109) US-19.2 Append-only repository with hash chaining | Siyabonga Jali | 1 |
| US-19 | [#110](https://github.com/olumafecode/agentsentinel/issues/110) US-19.3 verify-chain command and a tamper test | Siyabonga Jali | 2 |
| US-19 | [#111](https://github.com/olumafecode/agentsentinel/issues/111) US-19.4 Database role that can insert but not update or delete audit rows | Siyabonga Jali | 2 |
| US-19 | [#112](https://github.com/olumafecode/agentsentinel/issues/112) US-19.5 Audit completeness check (reused in US-26) | Siyabonga Jali | 2 |
| US-01 | [#104](https://github.com/olumafecode/agentsentinel/issues/104) US-01.1 Session-to-customer binding check in the gateway | Olusanya Mafe | 2 |
| US-01 | [#105](https://github.com/olumafecode/agentsentinel/issues/105) US-01.2 Per-task tool allowlist (moves into OPA in US-02a) | Olusanya Mafe | 2 |
| US-01 | [#106](https://github.com/olumafecode/agentsentinel/issues/106) US-01.3 End-to-end test AT-01 safe lookup | Olusanya Mafe | 2 |
| US-01 | [#107](https://github.com/olumafecode/agentsentinel/issues/107) US-01.4 Integration test AT-02 with a bank API call counter that must stay at zero | Olusanya Mafe | 2 |
| US-17 | [#94](https://github.com/olumafecode/agentsentinel/issues/94) US-17.1 Tool schemas and a gateway client for Vera | Siyabonga Jali | 2 |
| US-17 | [#95](https://github.com/olumafecode/agentsentinel/issues/95) US-17.2 Scripted fixtures for UC-01 to UC-07 | Siyabonga Jali | 2 |
| US-17 | [#96](https://github.com/olumafecode/agentsentinel/issues/96) US-17.3 Scenario runner command (run one fixture or all) | Siyabonga Jali | 2 |
| US-17 | [#97](https://github.com/olumafecode/agentsentinel/issues/97) US-17.4 Unit tests for the agent loop and refusal handling | Siyabonga Jali | 2 |

Changes from the suggested tasks:

- US-16.4 covers the bank API's Dockerfile and health endpoint. US-20.1 and US-20.3 cover the gateway and the shared conventions, so the work is not done twice.
- [Any other change you made on the board, or "None"]

## Risks and dependencies

| Risk or dependency | Effect | What we do |
|---|---|---|
| 29 points against a one-week velocity of 15, with Thanksgiving in week 2 | We may not finish everything | Check progress at the 25 November scrum. If behind, move US-17 to Sprint 2 and drive the M2 demo with test calls to the gateway |
| US-18 is at the 8-point limit | It may run over | Split the signed token (US-18.4) into its own story if needed |
| US-17 needs US-18.1 and US-16.1; US-19 needs PostgreSQL from US-20.2; US-01 needs US-18.2 and US-18.3 | Later tasks wait on earlier ones | Week 1 builds the contracts, the bank API, the Compose file and the database first |
| Docker Desktop on Windows may need WSL 2 and a restart | Lost time at the start | Both of us install and test Docker Desktop by 19 November |
| The token signing key is a secret, and the repository is public | The key could leak | Keep it in `.env`, which git ignores; commit only `.env.example` with a placeholder |
| Sprint 0 pull requests had no second reviewer (retrospective action) | Mistakes reach `main` unseen | Each of us approves the other's pull requests |

## Checklist

- [x] Every selected story meets the Definition of Ready
- [x] Every task has an owner
- [x] Ceremony checklist for this sprint moved to In progress
