# AgentSentinel product backlog

This file is the baseline product backlog and traceability record. It is generated from `tools/board/backlog.json`, the same file the board setup script reads. Once the board exists, the board is the working copy: stories move, split and get re-estimated there. Regenerate this file at the end of each sprint if the plan changes.

IDs match the approved proposal: use cases UC-01 to UC-12, functional requirements FR-01 to FR-20, non-functional requirements NFR-01 to NFR-14, acceptance tests AT-01 to AT-15 and user stories US-01 to US-11. Proposal stories that were too large for one sprint are split with a letter (US-02a and US-02b). Stories US-12 onward were added so that every piece of delivery work, including setup, data and evaluation, is on the board.

## Backlog at a glance

| Sprint | Dates | Sprint goal | Stories | Points |
|---|---|---|---|---|
| Sprint 0: Foundation | 9 Nov to 15 Nov 2026 | Board, repository rules, CI and the requirements baseline are in place, and milestone M1 is signed off. | US-12, US-13, US-14, US-10, US-15 | 15 |
| Sprint 1: First protected call | 16 Nov to 29 Nov 2026 | One ALLOW and one BLOCK flow run end to end through the gateway and are fully audited (M2). | US-16, US-17, US-18, US-01, US-19, US-20 | 29 |
| Sprint 2: Hybrid decision layer | 30 Nov to 13 Dec 2026 | OPA policy, data-origin checks, machine learning risk scoring and policy-cited explanations work together (M3). | US-02a, US-02b, US-21, US-04, US-06a | 34 |
| Sprint 3: Governance and platform | 14 Dec to 3 Jan 2027 | Approvals, quarantine, incident timeline, dashboard, Kubernetes profile and public deployment are working (M4). | US-03, US-05, US-06b, US-22, US-23, US-11a | 36 |
| Sprint 4: Evaluation and hardening | 4 Jan to 17 Jan 2027 | Security, utility, latency and resilience are measured against the targets; feature freeze at sprint end (M5, M6). | US-24, US-09, US-25, US-26, US-27, US-29 | 29 |
| Sprint 5: Release | 18 Jan to 24 Jan 2027 | Submission package complete and submitted by Sunday 24 January (M7). | US-11b | 5 |
| Contingency: Buffer only | 25 Jan to 30 Jan 2027 | No planned work. Used only if the 24 January submission slips; final cut-off 30 January. | None | 0 |
| Not scheduled | | Pulled in at sprint planning only if capacity allows | US-07, US-08, US-28, US-30 | 14 |

Must-have work totals 148 story points across 29 stories. Should and Could items are the first to drop if velocity is lower than planned; Won't items are listed so the scope decision is visible.

## Features

| Feature | Description | Stories |
|---|---|---|
| F-01 Project foundation and SDLC baseline | Everything the team needs before product code: board, repository rules, CI, requirements baseline and data schema. | US-12, US-13, US-14 |
| F-02 Synthetic bank and banking agent (Vera) | The fictional bank, its tools and the AI agent whose actions AgentSentinel governs. | US-15, US-16, US-17, US-24 |
| F-03 Interception, identity and scope | The gateway every protected tool call must pass through, with agent, user, session and customer binding. | US-18, US-01 |
| F-04 Policy, validation and data provenance | Bank rules written as code in OPA, checks on action details, and tracking where sensitive values came from. | US-02a, US-02b |
| F-05 Machine learning risk engine | Labelled synthetic data and the model that scores risky actions and sequences. | US-21, US-04 |
| F-06 Human approval and containment | Maker-checker approval for high-impact actions and quarantine for repeat offenders. | US-03, US-05 |
| F-07 Audit, explanation and incident evidence | Hash-linked audit trail, policy-cited explanations and incident timelines. | US-19, US-06a, US-06b |
| F-08 Dashboard and administration | The screens analysts, approvers and administrators use. | US-22, US-07, US-08, US-28, US-30 |
| F-09 Platform: containers, CI/CD, Kubernetes and observability | Docker, the CI/CD pipeline, public deployment, the Kubernetes profile, metrics, logs and traces. | US-10, US-20, US-23, US-11a, US-09 |
| F-10 Evaluation, hardening and release | AgentDojo and scenario evaluation, performance and security testing, and the submission package. | US-25, US-26, US-27, US-29, US-11b |

## User stories

| ID | Story | Feature | Priority | Points | Sprint | Milestone | Use cases | FR | NFR | Tests |
|---|---|---|---|---|---|---|---|---|---|---|
| US-12 | Set up the Scrum board and product backlog | F-01 | Must | 2 | Sprint 0 | M1 |  |  |  |  |
| US-13 | Create the repository with review rules and templates | F-01 | Must | 3 | Sprint 0 | M1 |  |  | NFR-09, NFR-14 |  |
| US-14 | Commit the requirements and design baseline | F-01 | Must | 3 | Sprint 0 | M1 |  |  |  |  |
| US-10 | Run automated checks on every pull request | F-09 | Must | 5 | Sprint 0 | M1 |  |  | NFR-09, NFR-14 |  |
| US-15 | Define the synthetic data schema | F-02 | Must | 2 | Sprint 0 | M1 |  |  | NFR-08 |  |
| US-16 | Build the synthetic demo bank API | F-02 | Must | 3 | Sprint 1 | M2 | UC-01 |  | NFR-08, NFR-10 |  |
| US-17 | Run Vera in scripted mode through the gateway only | F-02 | Must | 5 | Sprint 1 | M2 | UC-01 | FR-01 | NFR-14 |  |
| US-18 | Intercept every protected tool call at the gateway | F-03 | Must | 8 | Sprint 1 | M2 | UC-01 | FR-01, FR-02, FR-08, FR-09 | NFR-01, NFR-02, NFR-03, NFR-06 | AT-01 |
| US-01 | Keep Vera inside the current customer's data | F-03 | Must | 5 | Sprint 1 | M2 | UC-01, UC-04 | FR-02, FR-03, FR-08, FR-09, FR-13 | NFR-01, NFR-03, NFR-06 | AT-01, AT-02 |
| US-19 | Write a hash-linked audit event for every decision | F-07 | Must | 5 | Sprint 1 | M2 | UC-01, UC-09 | FR-13 | NFR-06 | AT-01 |
| US-20 | Run the whole stack with one Docker Compose command | F-09 | Must | 3 | Sprint 1 | M2 |  | FR-19 | NFR-10, NFR-14 |  |
| US-02a | Block unsafe tool calls with versioned OPA policy | F-04 | Must | 5 | Sprint 2 | M3 | UC-05 | FR-03, FR-04, FR-06, FR-08, FR-09, FR-13, FR-17 | NFR-01, NFR-03 | AT-03, AT-12 |
| US-02b | Block refunds whose details came from untrusted content | F-04 | Must | 8 | Sprint 2 | M3 | UC-02 | FR-05, FR-06, FR-08, FR-09, FR-13 | NFR-01, NFR-03, NFR-06 | AT-06 |
| US-21 | Generate the labelled synthetic action dataset | F-05 | Must | 5 | Sprint 2 | M3 | UC-06 | FR-07 | NFR-08, NFR-14 |  |
| US-04 | Score suspicious actions and sequences | F-05 | Must | 8 | Sprint 2 | M3 | UC-06 | FR-07, FR-08, FR-09, FR-13, FR-18 | NFR-02, NFR-03, NFR-06 | AT-07 |
| US-06a | Explain blocked and held decisions with policy citations | F-07 | Must | 8 | Sprint 2 | M3 | UC-08 | FR-12, FR-13 | NFR-02, NFR-07 | AT-09 |
| US-03 | Hold large refunds for human approval | F-06 | Must | 8 | Sprint 3 | M4 | UC-03 | FR-04, FR-08, FR-10, FR-11, FR-13 | NFR-01, NFR-06, NFR-12 | AT-04, AT-05 |
| US-05 | Quarantine an agent after repeated violations | F-06 | Must | 5 | Sprint 3 | M4 | UC-07 | FR-08, FR-09, FR-16, FR-18, FR-20 | NFR-01, NFR-03, NFR-06 | AT-08 |
| US-06b | Reconstruct an incident by correlation ID | F-07 | Must | 5 | Sprint 3 | M4 | UC-09 | FR-13, FR-14, FR-15 | NFR-06, NFR-11 | AT-10 |
| US-22 | Show decisions and agent status on a security dashboard | F-08 | Must | 5 | Sprint 3 | M4 | UC-06 | FR-15, FR-20 | NFR-12 |  |
| US-23 | Deploy a Kubernetes profile that self-heals and blocks bypass | F-09 | Must | 8 | Sprint 3 | M5 | UC-12 | FR-09, FR-19 | NFR-01, NFR-04, NFR-05, NFR-10 | AT-14, AT-15 |
| US-11a | Deploy to a public URL from main | F-09 | Must | 5 | Sprint 3 | M5 |  |  | NFR-04, NFR-14 |  |
| US-24 | Run Vera with a live LLM through a provider adapter | F-02 | Must | 3 | Sprint 4 | M6 | UC-02 | FR-01 | NFR-14 |  |
| US-09 | Expose health, latency, error and decision metrics | F-09 | Must | 5 | Sprint 4 | M5 | UC-12 | FR-15, FR-19 | NFR-04, NFR-11 |  |
| US-25 | Measure protection with the AgentDojo banking suite | F-10 | Must | 8 | Sprint 4 | M6 | UC-02 |  | NFR-01, NFR-14 |  |
| US-26 | Measure the scenario suite against the success targets | F-10 | Must | 5 | Sprint 4 | M6 |  |  | NFR-03, NFR-06, NFR-07 | AT-01, AT-02, AT-03, AT-05, AT-06, AT-07, AT-08, AT-09, AT-10 |
| US-27 | Test performance, failure and recovery | F-10 | Must | 5 | Sprint 4 | M6 | UC-12 |  | NFR-02, NFR-04, NFR-05, NFR-13 | AT-12, AT-13, AT-14, AT-15 |
| US-29 | Try to bypass the gateway and tamper with evidence | F-10 | Must | 3 | Sprint 4 | M6 |  | FR-09 | NFR-01 |  |
| US-11b | Package and submit the capstone | F-10 | Must | 5 | Sprint 5 | M7 |  |  | NFR-14 |  |
| US-07 | Simulate a policy change before activation | F-08 | Should | 5 |  |  | UC-10 | FR-06, FR-17 | NFR-09, NFR-14 | AT-11 |
| US-08 | Register agents with roles, tools and thresholds | F-08 | Should | 5 |  |  | UC-11 | FR-02, FR-03, FR-16, FR-17 | NFR-01, NFR-09, NFR-12 |  |
| US-28 | Check usability with people outside the team | F-08 | Should | 2 |  |  |  |  | NFR-12 |  |
| US-30 | Send critical alerts to email or a webhook | F-08 | Could | 2 |  |  | UC-07 | FR-20 |  |  |
| US-31 | Enterprise single sign-on (SSO) |  | Won't |  |  |  |  |  |  |  |
| US-32 | Real bank connectors and real money movement |  | Won't |  |  |  |  |  |  |  |
| US-33 | Advanced multi-agent control |  | Won't |  |  |  |  |  |  |  |
| US-34 | Real-time regulatory reporting |  | Won't |  |  |  |  |  |  |  |

## Story details

### US-12 Set up the Scrum board and product backlog

*Must | 2 points | Sprint 0 | F-01 Project foundation and SDLC baseline | Source: Handbook requirement: web-based Scrum board linked from the repository*

As the Scrum Master, I want a public Scrum board that holds the product backlog, sprints, stories and tasks with their status, so that the team and the grader can see what is planned, in progress and done at any time.

Acceptance criteria:
- Given the setup script has run, when anyone opens the board link, then they can see the product backlog (project visibility is public).
- Given a story on the board, when it is opened, then it shows its feature, sprint, priority, story points, FR, NFR and use case labels, and its tasks with completion progress.
- Given the repository README, when a reader opens it, then a Scrum board link points to the board and the board appears in the repository's Projects tab.

Traceability: use cases None; FR None; NFR None; tests None.

Suggested tasks (confirmed at sprint planning):
1. Run tools/board/setup_board.py and check that features, stories and Sprint 0 tasks were created (Scrum Master)
2. Create the board views listed in docs/agile/board-guide.md (Scrum Master)
3. Turn on the built-in workflows listed in docs/agile/board-guide.md (Scrum Master)
4. Add the board link to the README and confirm the board shows in the repository's Projects tab (Scrum Master)
5. Hold the start-up meeting and Sprint 0 planning; save notes in docs/agile/sprints/sprint-0/ (Whole team)

### US-13 Create the repository with review rules and templates

*Must | 3 points | Sprint 0 | F-01 Project foundation and SDLC baseline | Source: New story added for delivery*

As a Code Owner, I want a protected main branch, CODEOWNERS, issue and pull request templates and a contribution guide, so that every change is reviewed and linked to a story before it is merged.

Acceptance criteria:
- Given a pull request to main, when it lacks a Code Owner approval or CI is failing, then GitHub blocks the merge.
- Given a new issue, when a team member opens the issue form, then they can choose the User story, Task or Bug template with its required fields.
- Given the repository settings, when collaborators are checked, then the quantic-grader account has read access.

Traceability: use cases None; FR None; NFR NFR-09, NFR-14; tests None.

Suggested tasks (confirmed at sprint planning):
1. Create the repository and give the quantic-grader account read access (Product Owner)
2. Commit the starter files from this kit (README, CONTRIBUTING, CODEOWNERS, templates, .gitignore) (Code Owner)
3. Create the folder structure from proposal Section 16.1 with a short README in each folder (Developer)
4. Add a ruleset on main: pull request required, one approval, Code Owner review, status check ci required, no force push (Code Owner)
5. Turn on secret scanning, push protection and Dependabot alerts (Code Owner)

### US-14 Commit the requirements and design baseline

*Must | 3 points | Sprint 0 | F-01 Project foundation and SDLC baseline | Source: Proposal Section 6 (SDLC phases 1 to 3) and Section 13 (Sprint 0)*

As the Product Owner, I want the use cases, requirements, threat model, architecture and initial ADRs committed to the repository, so that every story traces back to an agreed requirement and design decision.

Acceptance criteria:
- Given docs/requirements, when a reviewer opens it, then UC-01 to UC-12, FR-01 to FR-20 and NFR-01 to NFR-14 are listed with the same IDs as the proposal and the board labels.
- Given docs/adr, when a reviewer opens it, then ADR-001 to ADR-008 exist with context, decision, consequences and status.
- Given any story, when the traceability tables are checked, then its use cases, FRs, NFRs and acceptance tests can be found.
- Given the Sprint 0 review, when the Product Owner accepts the baseline, then milestone M1 is recorded as signed off.

Traceability: use cases None; FR None; NFR None; tests None.

Suggested tasks (confirmed at sprint planning):
1. Write docs/requirements/requirements.md from proposal Sections 4 and 5 (Product Owner)
2. Write ADR-001 to ADR-008 as Markdown files in docs/adr (Developer)
3. Add the threat model table and architecture diagrams to docs/architecture (Developer)
4. Commit docs/agile/product-backlog.md as the traceability baseline (Scrum Master)
5. Product Owner signs off M1 at the Sprint 0 review (Product Owner)

### US-10 Run automated checks on every pull request

*Must | 5 points | Sprint 0 | F-09 Platform: containers, CI/CD, Kubernetes and observability | Source: Proposal Appendix B, US-10*

As a developer, I want every pull request linted, tested and scanned automatically, so that defects and leaked secrets are stopped before they reach main.

Acceptance criteria:
- Given a pull request, when it is opened or updated, then the ci workflow runs lint, unit tests and policy tests and reports pass or fail.
- Given a failing check, when CI finishes, then the pull request cannot be merged.
- Given a dependency with a known vulnerability or a committed secret, when scanning runs, then it is reported before merge.

Traceability: use cases None; FR None; NFR NFR-09, NFR-14; tests None.

Suggested tasks (confirmed at sprint planning):
1. Commit .github/workflows/ci.yml (Ruff lint, pytest, opa test) from the kit and make it pass (Developer)
2. Add pip-audit dependency scanning and Dependabot version updates (Developer)
3. Add a first smoke test so the pipeline runs green on main (Developer)
4. Make ci a required status check in the main branch ruleset (Code Owner)
5. Add pre-commit hooks for formatting and lint (Developer)

### US-15 Define the synthetic data schema

*Must | 2 points | Sprint 0 | F-02 Synthetic bank and banking agent (Vera) | Source: Proposal Section 8.3 and Section 13 (Sprint 0: synthetic data schema)*

As a developer, I want one documented schema for synthetic customers, accounts, transactions, sessions and agent actions, so that every service and test uses the same invented data and no real personal data enters the project.

Acceptance criteria:
- Given the schema document, when a developer reads it, then each entity in proposal Section 7.4 has its fields, types and example values.
- Given the generator rules, when data is produced, then names, account numbers and emails are clearly synthetic (reserved test domains, fixed fake formats).
- Given the labelling rules, when an action event is created, then its expected outcome and failure mode are recorded.

Traceability: use cases None; FR None; NFR NFR-08; tests None.

Suggested tasks (confirmed at sprint planning):
1. Write Pydantic models or JSON Schemas for the Section 7.4 entities (Developer)
2. Write labelling rules for normal actions and the five failure modes (Product Owner)
3. Document synthetic-data rules: reserved domains, fake account formats, fixed random seed (Developer)
4. Review the schema against what FR-04, FR-05 and FR-07 need (Code Owner)

### US-16 Build the synthetic demo bank API

*Must | 3 points | Sprint 1 | F-02 Synthetic bank and banking agent (Vera) | Source: New story added for delivery*

As a demo presenter, I want a demo bank API with customers, accounts, transactions, refunds and admin tools filled with invented data, so that Vera has realistic tools to call.

Acceptance criteria:
- Given the seeded database, when transactions are requested for a customer, then only that customer's synthetic transactions are returned.
- Given a request without a valid gateway execution token, when it reaches a protected endpoint, then the bank API rejects it with HTTP 403.
- Given the reset command, when it runs, then the demo bank returns to the same seeded state.

Traceability: use cases UC-01; FR None; NFR NFR-08, NFR-10; tests None.

Suggested tasks (confirmed at sprint planning):
1. FastAPI service with tools: get_customer, get_transactions, update_address, issue_refund, close_dispute, export_customers, admin tools (Developer)
2. Seed generator with a fixed seed and a demo reset command (Developer)
3. Unit tests for each endpoint (Developer)
4. Dockerfile and health endpoint (Developer)

### US-17 Run Vera in scripted mode through the gateway only

*Must | 5 points | Sprint 1 | F-02 Synthetic bank and banking agent (Vera) | Source: New story added for delivery*

As a demo presenter, I want Vera to propose tool calls only through the AgentSentinel gateway, with a deterministic scripted mode, so that every scenario can be replayed the same way and the agent never holds bank credentials.

Acceptance criteria:
- Given Vera's configuration, when it is inspected, then it holds the gateway URL and no bank API URL or credential.
- Given a scripted fixture, when it runs twice, then Vera proposes the same tool calls in the same order.
- Given a BLOCK decision, when Vera receives it, then Vera tells the user the action was refused and does not retry the same call.

Traceability: use cases UC-01; FR FR-01; NFR NFR-14; tests None.

Suggested tasks (confirmed at sprint planning):
1. Tool schemas and a gateway client for Vera (Developer)
2. Scripted fixtures for UC-01 to UC-07 (Developer)
3. Scenario runner command (run one fixture or all) (Developer)
4. Unit tests for the agent loop and refusal handling (Developer)

### US-18 Intercept every protected tool call at the gateway

*Must | 8 points | Sprint 1 | F-03 Interception, identity and scope | Source: New story added for delivery*

As a security analyst, I want every protected tool call intercepted before execution and bound to agent, user, session, task and correlation context, so that nothing reaches the bank API without a decision.

Acceptance criteria:
- Given any protected tool call from Vera, when it is sent, then the gateway evaluates it first and returns ALLOW, HUMAN_REVIEW, BLOCK or QUARANTINE with a correlation ID.
- Given an ALLOW decision, when the gateway forwards the call, then it attaches a signed single-use execution token that the bank API verifies; a replayed token is rejected.
- Given an unknown tool or missing context, when the gateway evaluates it, then the decision is BLOCK (deny by default).
- Given the same correlation ID twice, when the gateway evaluates it, then it returns the same decision and the action executes at most once.

Traceability: use cases UC-01; FR FR-01, FR-02, FR-08, FR-09; NFR NFR-01, NFR-02, NFR-03, NFR-06; tests AT-01.

Suggested tasks (confirmed at sprint planning):
1. Define ProtectedActionRequest and GovernanceDecision contracts (Pydantic) from proposal Appendix E (Developer)
2. Build POST /v1/actions/evaluate with context binding from token and session claims (Developer)
3. Decision orchestrator with deny by default and the Appendix E precedence order (Developer)
4. Signed single-use execution token issued by the gateway and verified by the bank API (Developer)
5. Idempotent decisions by correlation ID (Developer)
6. Unit and contract tests, including a token replay attempt (Developer)

### US-01 Keep Vera inside the current customer's data

*Must | 5 points | Sprint 1 | F-03 Interception, identity and scope | Source: Proposal Appendix B, US-01*

As a bank customer, I want Vera to retrieve only my authorized information, so that AI assistance does not expose another customer's data.

Acceptance criteria:
- Given Customer A's session, when Vera asks for Customer A's recent transactions, then the decision is ALLOW and the data is returned (AT-01).
- Given Customer A's session, when Vera asks for Customer B's records, then the decision is BLOCK and the bank API receives no call (AT-02).
- Given either case, when the audit log is checked, then one complete audit event exists for the correlation ID.

Traceability: use cases UC-01, UC-04; FR FR-02, FR-03, FR-08, FR-09, FR-13; NFR NFR-01, NFR-03, NFR-06; tests AT-01, AT-02.

Suggested tasks (confirmed at sprint planning):
1. Session-to-customer binding check in the gateway (Developer)
2. Per-task tool allowlist (moves into OPA in US-02a) (Developer)
3. End-to-end test AT-01 safe lookup (Developer)
4. Integration test AT-02 with a bank API call counter that must stay at zero (Developer)

### US-19 Write a hash-linked audit event for every decision

*Must | 5 points | Sprint 1 | F-07 Audit, explanation and incident evidence | Source: New story added for delivery*

As an auditor, I want every evaluated action written as an append-only, hash-linked audit event, so that the decision path can be reconstructed and tampering can be detected.

Acceptance criteria:
- Given any decision, when it is made, then an audit event is stored with correlation ID, actor, tool, arguments, decision, policy and model versions, timestamps, previous hash and own hash.
- Given the stored chain, when one event is edited directly in the database, then the verify-chain command reports the broken link.
- Given the gateway's database role, when it tries to update or delete audit rows, then the database refuses.

Traceability: use cases UC-01, UC-09; FR FR-13; NFR NFR-06; tests AT-01.

Suggested tasks (confirmed at sprint planning):
1. PostgreSQL schema and migrations for ToolCall and AuditEvent (Developer)
2. Append-only repository with hash chaining (Developer)
3. verify-chain command and a tamper test (Developer)
4. Database role that can insert but not update or delete audit rows (Developer)
5. Audit completeness check (reused in US-26) (Developer)

### US-20 Run the whole stack with one Docker Compose command

*Must | 3 points | Sprint 1 | F-09 Platform: containers, CI/CD, Kubernetes and observability | Source: New story added for delivery*

As a developer, I want every service containerized and started with one docker compose command, so that the system runs the same way on every machine and in CI.

Acceptance criteria:
- Given a clean machine with Docker, when docker compose up runs, then the bank API, gateway, OPA and PostgreSQL with pgvector start and pass their health checks.
- Given a merge to main, when CI runs, then images are built with the commit SHA as tag and scanned with Trivy; critical findings fail the build.
- Given any service, when /healthz and /readyz are called, then they report liveness and readiness.

Traceability: use cases None; FR FR-19; NFR NFR-10, NFR-14; tests None.

Suggested tasks (confirmed at sprint planning):
1. Dockerfiles: slim base image, non-root user, pinned versions (Developer)
2. docker-compose.yml with health checks and .env.example (Developer)
3. /healthz and /readyz on every service (Developer)
4. CI job: build images tagged with the commit SHA, scan with Trivy, push to GitHub Container Registry on main (Developer)

### US-02a Block unsafe tool calls with versioned OPA policy

*Must | 5 points | Sprint 2 | F-04 Policy, validation and data provenance | Source: Proposal Appendix B, US-02 (split: hard policy blocks)*

As a security analyst, I want bulk exports, wrong tools and invalid action details blocked by versioned bank policy before execution, so that a well-formed but unsafe request cannot cause harm.

Acceptance criteria:
- Given a request to export all customers, when it is evaluated, then OPA denies it, the decision is BLOCK and the bank API is not called (AT-03).
- Given a refund with a negative or out-of-range amount, or a tool not allowed for the current task, when it is evaluated, then the decision is BLOCK with a reason code.
- Given any decision, when it is audited, then the policy bundle version and matched rules are recorded.
- Given OPA is unreachable, when a high-impact action is evaluated, then the gateway fails closed and logs the fault (AT-12).

Traceability: use cases UC-05; FR FR-03, FR-04, FR-06, FR-08, FR-09, FR-13, FR-17; NFR NFR-01, NFR-03; tests AT-03, AT-12.

Suggested tasks (confirmed at sprint planning):
1. Rego policies: task-to-tool permissions, bulk export deny, value ranges, refund threshold (Developer)
2. OPA container and gateway client with timeout and fail-closed handling (Developer)
3. Policy unit tests with opa test, including boundary values (Developer)
4. Versioned policy bundles; record policy_version in decisions and audit (Developer)
5. Integration test AT-03 (Developer)

### US-02b Block refunds whose details came from untrusted content

*Must | 8 points | Sprint 2 | F-04 Policy, validation and data provenance | Source: Proposal Appendix B, US-02 (split: prompt injection)*

As a security analyst, I want refund destinations and amounts that came from untrusted content such as emails or documents blocked or held, so that a prompt injection cannot redirect money.

Acceptance criteria:
- Given a support email with hidden instructions and an attacker account number, when Vera proposes a refund to that account, then the decision is BLOCK (or HUMAN_REVIEW if so configured) and the bank API is not called (AT-06).
- Given a refund whose account and amount match what the customer typed, when it is evaluated, then they are labelled trusted and normal rules apply.
- Given any decision, when it is audited, then the data-origin label of each sensitive parameter is recorded.

Traceability: use cases UC-02; FR FR-05, FR-06, FR-08, FR-09, FR-13; NFR NFR-01, NFR-03, NFR-06; tests AT-06.

Suggested tasks (confirmed at sprint planning):
1. Data-origin labels on Vera's context: trusted user input versus retrieved content (Developer)
2. Value-matching tracker for configured sensitive parameters (Developer)
3. Rego rule for untrusted sensitive parameters (Developer)
4. Poisoned email and document fixtures (Developer)
5. Scenario test AT-06 with a bank API call counter (Developer)

### US-21 Generate the labelled synthetic action dataset

*Must | 5 points | Sprint 2 | F-05 Machine learning risk engine | Source: New story added for delivery*

As an ML engineer, I want 2,000 to 5,000 labelled synthetic action events and short sequences, with a held-out test set frozen before tuning, so that the risk model is trained and judged fairly.

Acceptance criteria:
- Given the generator and its fixed seed, when it runs twice, then it produces the same dataset and checksum.
- Given the dataset, when it is split, then train, validation and test are 70/15/15 and the test set checksum is recorded before any tuning.
- Given each failure mode in proposal Section 2.1, when the dataset is inspected, then it contains labelled examples of that mode and of normal behavior.

Traceability: use cases UC-06; FR FR-07; NFR NFR-08, NFR-14; tests None.

Suggested tasks (confirmed at sprint planning):
1. Event and sequence generator for normal behavior and the five failure modes (Developer)
2. Apply the labelling rules in code and review a 50-event sample by hand (Product Owner)
3. 70/15/15 split with a frozen test set and checksums (Developer)
4. Dataset card: version, size, class balance, known limitations (Developer)

### US-04 Score suspicious actions and sequences

*Must | 8 points | Sprint 2 | F-05 Machine learning risk engine | Source: Proposal Appendix B, US-04*

As a security analyst, I want suspicious action sequences scored, so that unusual behavior is caught even when each single call looks valid.

Acceptance criteria:
- Given normal customer-service actions followed by unusual admin or export requests, when they are evaluated, then the risk is high and the decision is HUMAN_REVIEW, BLOCK or QUARANTINE per policy (AT-07).
- Given a hard policy deny, when the risk score is low, then the decision stays BLOCK (the model can add caution but never remove it).
- Given the validation set, when the baseline and the stronger model are compared, then precision, recall, F1 and confusion matrices are reported and the chosen model version is recorded.
- Given a scored action, when it is audited, then model_version and risk_score are recorded.

Traceability: use cases UC-06; FR FR-07, FR-08, FR-09, FR-13, FR-18; NFR NFR-02, NFR-03, NFR-06; tests AT-07.

Suggested tasks (confirmed at sprint planning):
1. Feature pipeline for the six feature families in proposal Section 8.1 (Developer)
2. Train a Logistic Regression baseline and a Random Forest or gradient boosting comparator; check Isolation Forest (Developer)
3. Risk engine service POST /score returning score, band and model_version (Developer)
4. Gateway integration with precedence rules and velocity limits (FR-18) (Developer)
5. Evaluation notebook on the validation set (Developer)

### US-06a Explain blocked and held decisions with policy citations

*Must | 8 points | Sprint 2 | F-07 Audit, explanation and incident evidence | Source: Proposal Appendix B, US-06 (split: explanation)*

As an auditor, I want a plain-English explanation of a blocked or held decision that cites the bank policy behind it, so that I can review the control without reading code.

Acceptance criteria:
- Given a blocked event, when the analyst opens it, then an explanation cites at least one policy section ID from the retrieved policy text (AT-09).
- Given the explanation service, when it runs, then it runs after the decision and cannot change the decision.
- Given a citation that is not in the retrieved set, when validation runs, then the explanation is rejected and a safe fallback message is shown.
- Given the external LLM is unavailable, when an explanation is requested, then the fallback is used and the security decision is unaffected.

Traceability: use cases UC-08; FR FR-12, FR-13; NFR NFR-02, NFR-07; tests AT-09.

Suggested tasks (confirmed at sprint planning):
1. Write the four synthetic bank policy documents with section IDs (Product Owner)
2. Chunk and embed the policies into pgvector (Developer)
3. RAG service POST /explain with a provider-neutral LLM adapter and mock fallback (Developer)
4. Validate citations against the retrieved set (Developer)
5. Call the explanation service after the decision and store ExplanationEvidence (Developer)

### US-03 Hold large refunds for human approval

*Must | 8 points | Sprint 3 | F-06 Human approval and containment | Source: Proposal Appendix B, US-03*

As a manager, I want large refunds held for approval, so that material financial actions remain under human control.

Acceptance criteria:
- Given a refund exactly at the automatic limit, when it is evaluated, then the outcome matches the policy boundary specification (AT-04).
- Given a refund above the limit, when it is evaluated, then the decision is HUMAN_REVIEW and nothing executes before approval (AT-05).
- Given a held refund, when the approver opens it, then they see the customer request, amount, reason, risk score and relevant policy in plain English.
- Given an approval or rejection, when it is saved, then the held action resumes or ends under the same correlation ID; an unauthorized approver, or the person who raised the request, is refused.

Traceability: use cases UC-03; FR FR-04, FR-08, FR-10, FR-11, FR-13; NFR NFR-01, NFR-06, NFR-12; tests AT-04, AT-05.

Suggested tasks (confirmed at sprint planning):
1. Approval service: create, expire, approve and reject with maker-checker rules (Developer)
2. Gateway HUMAN_REVIEW path that parks the action (Developer)
3. Resume or end held actions under the same correlation ID (Developer)
4. Approval screen with full context (Developer)
5. Tests AT-04, AT-05 and the unauthorized approver case (Developer)

### US-05 Quarantine an agent after repeated violations

*Must | 5 points | Sprint 3 | F-06 Human approval and containment | Source: Proposal Appendix B, US-05*

As a security analyst, I want repeated violations to quarantine an agent, so that compromised behavior is contained quickly.

Acceptance criteria:
- Given three or more prohibited calls inside the configured window, when the next call arrives, then the agent is QUARANTINED and every later call is denied (AT-08).
- Given a quarantine, when the dashboard is open, then a critical incident and a notification appear.
- Given an administrator, when they use the kill switch or release the agent, then the change is audited.

Traceability: use cases UC-07; FR FR-08, FR-09, FR-16, FR-18, FR-20; NFR NFR-01, NFR-03, NFR-06; tests AT-08.

Suggested tasks (confirmed at sprint planning):
1. Violation counter within a time window (Developer)
2. Quarantine state on the agent record, enforced by the gateway (Developer)
3. Kill switch and release action for administrators (Developer)
4. Critical incident notification on the dashboard (Developer)
5. Scenario test AT-08 (Developer)

### US-06b Reconstruct an incident by correlation ID

*Must | 5 points | Sprint 3 | F-07 Audit, explanation and incident evidence | Source: Proposal Appendix B, US-06 (split: incident timeline)*

As an auditor, I want to open an incident by correlation ID and see the ordered path from user request to outcome, so that I can reconstruct what happened.

Acceptance criteria:
- Given a prior incident, when it is opened by correlation ID, then the timeline shows request, tool call, data origin, policy result, risk score, approval, explanation and outcome in order (AT-10).
- Given the timeline, when verify-chain runs over its events, then the chain is intact.
- Given each timeline step, when it is viewed, then it shows the trace ID that links it to logs and traces.

Traceability: use cases UC-09; FR FR-13, FR-14, FR-15; NFR NFR-06, NFR-11; tests AT-10.

Suggested tasks (confirmed at sprint planning):
1. Incident entity and creation rules (Developer)
2. Timeline API ordered by correlation ID (Developer)
3. Timeline screen (Developer)
4. Replay test AT-10 including chain verification (Developer)

### US-22 Show decisions and agent status on a security dashboard

*Must | 5 points | Sprint 3 | F-08 Dashboard and administration | Source: New story added for delivery*

As a security analyst, I want a dashboard of recent actions, risk scores, incidents, approvals, blocked actions, agent status and service health, so that I can see what the agent is doing at a glance.

Acceptance criteria:
- Given new decisions, when the dashboard is open, then they appear with a plain-English reason within a few seconds.
- Given a pending approval or critical incident, when the dashboard is open, then it is highlighted with a link to its detail screen.
- Given a keyboard-only user, when they move through the dashboard, then every control is reachable and text meets WCAG AA contrast.

Traceability: use cases UC-06; FR FR-15, FR-20; NFR NFR-12; tests None.

Suggested tasks (confirmed at sprint planning):
1. Dashboard shell and sign-in for analyst, approver and administrator roles (Developer)
2. Decision feed with reasons, risk scores and filters (Developer)
3. Agent status panel and pending approvals inbox (Developer)
4. Keyboard and contrast check (Developer)
5. Playwright end-to-end smoke test (Developer)

### US-23 Deploy a Kubernetes profile that self-heals and blocks bypass

*Must | 8 points | Sprint 3 | F-09 Platform: containers, CI/CD, Kubernetes and observability | Source: New story added for delivery*

As a platform engineer, I want a Kubernetes profile with probes, NetworkPolicy, autoscaling and rolling updates, so that the system self-heals, scales and the agent cannot reach bank tools directly.

Acceptance criteria:
- Given the kind or k3d cluster, when a gateway or risk engine pod is deleted, then the Deployment restores it without manual action (AT-14).
- Given NetworkPolicy, when the agent pod calls the bank API directly, then the connection is refused, while calls through the gateway work.
- Given load on the gateway, when CPU passes the target, then the autoscaler adds replicas (2 to 5).
- Given a new risk engine image, when it is rolled out, then health checks pass and rollback works (AT-15).

Traceability: use cases UC-12; FR FR-09, FR-19; NFR NFR-01, NFR-04, NFR-05, NFR-10; tests AT-14, AT-15.

Suggested tasks (confirmed at sprint planning):
1. Helm chart or Kustomize: Deployments, Services, ConfigMaps, Secrets, resource limits (Developer)
2. Readiness and liveness probes (Developer)
3. NetworkPolicy and a bypass test (Developer)
4. Horizontal Pod Autoscaler with metrics-server (Developer)
5. kind or k3d setup script and kubeconform validation in CI (Developer)
6. Rolling update and rollback script (Developer)

### US-11a Deploy to a public URL from main

*Must | 5 points | Sprint 3 | F-09 Platform: containers, CI/CD, Kubernetes and observability | Source: Proposal Appendix B, US-11 (split: public deployment)*

As a grader, I want a stable public URL deployed automatically from main, so that I can try the working system at any time.

Acceptance criteria:
- Given a merge to main with green CI, when the deploy job runs, then the public demo is updated and a smoke test checks health plus one ALLOW and one BLOCK scenario.
- Given the public demo, when it is opened, then only the dashboard and intended public APIs are reachable; internal services use private networking.
- Given the deployment, when it is inspected, then secrets are held in the platform's secret store and not in the repository.

Traceability: use cases None; FR None; NFR NFR-04, NFR-14; tests None.

Suggested tasks (confirmed at sprint planning):
1. ADR-009: choose Railway or Render, with cost and limits (Developer)
2. Deploy the services and managed PostgreSQL (Developer)
3. CD job on merge to main with a post-deploy smoke test (Developer)
4. Show the live URL in the README and the build SHA in the dashboard footer (Developer)

### US-24 Run Vera with a live LLM through a provider adapter

*Must | 3 points | Sprint 4 | F-02 Synthetic bank and banking agent (Vera) | Source: New story added for delivery*

As a demo presenter, I want Vera to run with a real LLM through a provider-neutral adapter, so that live scenarios and AgentDojo runs use a real agent while scripted mode stays as the fallback.

Acceptance criteria:
- Given LLM mode, when a UC-01 request is made, then Vera plans and proposes the tool call through the gateway.
- Given a recorded run, when it is inspected, then the model name, version and temperature are stored with the results.
- Given the provider is down, when the demo runs, then one setting switches Vera back to scripted mode.

Traceability: use cases UC-02; FR FR-01; NFR NFR-14; tests None.

Suggested tasks (confirmed at sprint planning):
1. LLM adapter interface with one provider and a mock (Developer)
2. Pinned model settings stored in run metadata (Developer)
3. Spend cap and timeout settings (Developer)
4. Live run of the UC-01 and UC-02 fixtures (Developer)

### US-09 Expose health, latency, error and decision metrics

*Must | 5 points | Sprint 4 | F-09 Platform: containers, CI/CD, Kubernetes and observability | Source: Proposal Appendix B, US-09*

As a platform engineer, I want health, latency, error, traffic, saturation and decision metrics, so that I can operate AgentSentinel like a production system.

Acceptance criteria:
- Given traffic, when the metrics dashboard is open, then it shows request rate, error rate, p95 latency, saturation and decision counts by outcome.
- Given a request, when it is traced, then the trace ID and correlation ID link logs, traces and audit events.
- Given a stopped dependency, when health is checked, then readiness turns false and the dashboard health tile shows it.

Traceability: use cases UC-12; FR FR-15, FR-19; NFR NFR-04, NFR-11; tests None.

Suggested tasks (confirmed at sprint planning):
1. OpenTelemetry tracing with correlation IDs (Developer)
2. Prometheus metrics for decisions and latency (Developer)
3. Grafana dashboard JSON committed to the repository (Developer)
4. Structured JSON logs (Developer)
5. Health tiles on the security dashboard (Developer)

### US-25 Measure protection with the AgentDojo banking suite

*Must | 8 points | Sprint 4 | F-10 Evaluation, hardening and release | Source: Proposal Section 8.4*

As the Product Owner, I want AgentDojo banking-suite runs for Setups A, B and C, so that we can show how much AgentSentinel lowers attack success while keeping normal tasks working.

Acceptance criteria:
- Given Setup A (no AgentSentinel), Setup B (deterministic checks only) and Setup C (full pipeline), when each runs on the same tasks and model, then attack success rate, benign utility and utility under attack are recorded.
- Given the results, when they are published, then the run scripts, model settings and raw outputs are in the repository so the numbers can be reproduced.
- Given a target that is not met, when the results are written up, then the gap is stated plainly.

Traceability: use cases UC-02; FR None; NFR NFR-01, NFR-14; tests None.

Suggested tasks (confirmed at sprint planning):
1. Install AgentDojo and route its banking tool calls through the gateway (Developer)
2. Run Setup A baseline (Developer)
3. Run Setups B and C (Developer)
4. Results table and charts in docs/results (Developer)

### US-26 Measure the scenario suite against the success targets

*Must | 5 points | Sprint 4 | F-10 Evaluation, hardening and release | Source: Proposal Sections 11 and 12*

As the Product Owner, I want the held-out scenario suite, model metrics, citation check, false-block rate and audit completeness measured against proposal Section 12, so that the final report shows measured values, not claims.

Acceptance criteria:
- Given the frozen test set, when the model is evaluated once, then recall, precision, F1 and false-block rate are reported against the targets.
- Given a sample of at least 30 explanations, when they are reviewed, then the share citing the correct policy is reported.
- Given all acceptance scenarios, when they run, then audit completeness is reported (target 100%).
- Given threshold tuning, when it happens, then it uses validation data only and the change is recorded.

Traceability: use cases None; FR None; NFR NFR-03, NFR-06, NFR-07; tests AT-01, AT-02, AT-03, AT-05, AT-06, AT-07, AT-08, AT-09, AT-10.

Suggested tasks (confirmed at sprint planning):
1. Scenario suite covering UC-01 to UC-11 with expected outcomes (Developer)
2. One-time evaluation on the frozen test set (Developer)
3. Explanation grounding review sheet (Product Owner)
4. Audit completeness report (Developer)
5. Results summary in docs/results (Developer)

### US-27 Test performance, failure and recovery

*Must | 5 points | Sprint 4 | F-10 Evaluation, hardening and release | Source: New story added for delivery*

As a platform engineer, I want load, failure and recovery tests, so that latency, fail-closed behavior and self-healing are measured rather than assumed.

Acceptance criteria:
- Given the agreed demo load in Locust, when the test runs, then p95 non-generative decision latency is measured against the 300 ms target (AT-13).
- Given OPA or the risk engine is stopped, when a high-impact action arrives, then it fails closed and is logged (AT-12).
- Given pod deletion and a rolling update, when they run, then recovery evidence is captured (AT-14, AT-15).
- Given a database export, when the demo is restored on a clean environment, then it takes under 30 minutes.

Traceability: use cases UC-12; FR None; NFR NFR-02, NFR-04, NFR-05, NFR-13; tests AT-12, AT-13, AT-14, AT-15.

Suggested tasks (confirmed at sprint planning):
1. Locust load test and p95 report (Developer)
2. Dependency outage tests for fail-closed behavior (Developer)
3. Recovery evidence: screenshots and logs (Developer)
4. Backup, restore and a timed rebuild (Developer)

### US-29 Try to bypass the gateway and tamper with evidence

*Must | 3 points | Sprint 4 | F-10 Evaluation, hardening and release | Source: Proposal Section 14 (security bypass risk: explicit penetration tests)*

As a security analyst, I want the team to attack its own controls, so that bypass, replay and tamper weaknesses are found before a reviewer finds them.

Acceptance criteria:
- Given direct calls from the agent to the bank API (Docker Compose and Kubernetes), when they are attempted, then they fail.
- Given a captured execution token, when it is replayed, then it is rejected.
- Given a direct edit of an audit row, when verify-chain runs, then the tampering is reported.
- Given any finding, when it is confirmed, then it is logged as a bug on the board and fixed or documented.

Traceability: use cases None; FR FR-09; NFR NFR-01; tests None.

Suggested tasks (confirmed at sprint planning):
1. Bypass test script for Docker Compose and Kubernetes (Developer)
2. Token replay and expiry tests (Developer)
3. Audit tamper test (Developer)
4. Log findings as bugs and fix them (Developer)

### US-11b Package and submit the capstone

*Must | 5 points | Sprint 5 | F-10 Evaluation, hardening and release | Source: Proposal Appendix B, US-11 (split: submission package) and handbook submission list*

As a grader, I want a reproducible repository setup, a design and testing document and a final demonstration video, so that I can evaluate the working system.

Acceptance criteria:
- Given a clean machine, when a reader follows the README quickstart, then tests and core scenarios run with version-pinned dependencies and a sample environment file.
- Given the README, when the grader opens it, then it links to the live demo, the Scrum board, the design and testing document and the video.
- Given the design and testing document, when it is reviewed, then it covers architecture decisions, patterns, deployment options with cost, and every test type with measured results.
- Given the video, when it plays, then it runs 15 to 20 minutes and every team member speaks on camera.

Traceability: use cases None; FR None; NFR NFR-14; tests None.

Suggested tasks (confirmed at sprint planning):
1. Final README: links, quickstart and test commands (Developer)
2. Design and testing document with measured results (Whole team)
3. Final traceability: story to FR, NFR, test and evidence (Scrum Master)
4. Rehearse and record the 15 to 20 minute video (Whole team)
5. Board clean-up, release tag v1.0.0 and submission by 24 January (Scrum Master)

### US-07 Simulate a policy change before activation

*Should | 5 points | not scheduled | F-08 Dashboard and administration | Source: Proposal Appendix B, US-07*

As an administrator, I want to simulate a policy change against stored synthetic events before activation, so that changes do not unexpectedly block customers.

Acceptance criteria:
- Given a candidate policy bundle, when simulation runs on stored events, then a report lists the decisions that would change (AT-11).
- Given a simulation, when it finishes, then the active policy is unchanged.
- Given the administrator activates the candidate, when it goes live, then the new version is audited.

Traceability: use cases UC-10; FR FR-06, FR-17; NFR NFR-09, NFR-14; tests AT-11.

Suggested tasks (confirmed at sprint planning):
1. Store policy bundle versions (Developer)
2. Replay stored events against a candidate bundle (Developer)
3. Difference report (Developer)
4. Activation step with audit (Developer)

### US-08 Register agents with roles, tools and thresholds

*Should | 5 points | not scheduled | F-08 Dashboard and administration | Source: Proposal Appendix B, US-08*

As a platform engineer, I want to register agents with explicit roles, tools and thresholds, so that least privilege is manageable.

Acceptance criteria:
- Given an administrator, when they register an agent with a role and allowed tools, then the gateway enforces those tools straight away.
- Given a user who is not an administrator, when they try to change an agent, then the request is refused and audited.
- Given an agent, when an administrator disables it, then all its calls are denied.

Traceability: use cases UC-11; FR FR-02, FR-03, FR-16, FR-17; NFR NFR-01, NFR-09, NFR-12; tests None.

Suggested tasks (confirmed at sprint planning):
1. Agent and ToolDefinition tables with an admin API (Developer)
2. Registry feeds the OPA data bundle (Developer)
3. Admin form on the dashboard (Developer)
4. Authorization tests (Developer)

### US-28 Check usability with people outside the team

*Should | 2 points | not scheduled | F-08 Dashboard and administration | Source: Proposal Section 11.1 (usability testing)*

As an approver, I want the dashboard to be clear and easy to use under time pressure, so that I approve or reject the right actions.

Acceptance criteria:
- Given three people outside the team, when they complete approve, reject and incident-review tasks, then completion and points of confusion are recorded.
- Given the findings, when they are reviewed, then the top issues are fixed or logged as backlog items.

Traceability: use cases None; FR None; NFR NFR-12; tests None.

Suggested tasks (confirmed at sprint planning):
1. Write three usability tasks and a short checklist (Product Owner)
2. Run the sessions and record notes (Product Owner)
3. Fix or log the top issues (Developer)

### US-30 Send critical alerts to email or a webhook

*Could | 2 points | not scheduled | F-08 Dashboard and administration | Source: Proposal FR-20 (optional demo email/webhook adapter)*

As a security analyst, I want critical incidents and pending approvals sent to a demo email address or webhook, so that I notice them when the dashboard is closed.

Acceptance criteria:
- Given a quarantine or a pending approval, when it happens, then a webhook message with the correlation ID is sent.
- Given the adapter is switched off, when an incident happens, then the dashboard notification still appears.

Traceability: use cases UC-07; FR FR-20; NFR None; tests None.

Suggested tasks (confirmed at sprint planning):
1. Notification adapter interface (Developer)
2. Webhook implementation and test (Developer)

## Won't have in this release

- **US-31 Enterprise single sign-on (SSO).** Enterprise SSO is outside the capstone release (proposal Section 5.3).
- **US-32 Real bank connectors and real money movement.** No real bank connectivity, data or payments (proposal Section 3 scope).
- **US-33 Advanced multi-agent control.** Multi-agent control is outside the capstone release (proposal Section 5.3).
- **US-34 Real-time regulatory reporting.** Real-time regulatory reporting is outside the capstone release (proposal Section 5.3).

## Traceability

Every functional and non-functional requirement is delivered by at least one Must-have story. On the board, filter by the requirement's label (for example `label:FR-05`) to see the same list live.

### Functional requirements to stories

| FR | Requirement | Delivered by |
|---|---|---|
| FR-01 | Intercept every protected tool/API call before execution. | US-17, US-18, US-24 |
| FR-02 | Authenticate/identify the agent and bind the action to user, session, task, and correlation context. | US-18, US-01, US-08 (Should) |
| FR-03 | Enforce task/tool permissions and least-privilege scopes. | US-01, US-02a, US-08 (Should) |
| FR-04 | Validate structured action details such as amount, account identifier, target resource, and allowed value ranges. | US-02a, US-03 |
| FR-05 | Record data provenance for configured sensitive parameters and distinguish trusted user intent from untrusted retrieved content. | US-02b |
| FR-06 | Evaluate deterministic bank policy using Open Policy Agent or an equivalent policy engine. | US-02a, US-02b, US-07 (Should) |
| FR-07 | Calculate a configurable machine-learning risk/anomaly score for selected actions and short action sequences. | US-21, US-04 |
| FR-08 | Produce one enforceable decision: ALLOW, HUMAN_REVIEW, BLOCK, or QUARANTINE. | US-18, US-01, US-02a, US-02b, US-04, US-03, US-05 |
| FR-09 | Prevent blocked/quarantined actions from reaching protected bank APIs. | US-18, US-01, US-02a, US-02b, US-04, US-05, US-23, US-29 |
| FR-10 | Create approval requests for configured high-impact actions and allow authorized users to approve or reject them. | US-03 |
| FR-11 | Resume or terminate the held action according to the approval outcome without losing audit context. | US-03 |
| FR-12 | Provide a plain-English decision explanation grounded in retrieved policy evidence and citation identifiers. | US-06a |
| FR-13 | Write an audit event for every evaluated action, including decision inputs, policy/model versions, risk result, final outcome, and timestamps. | US-01, US-19, US-02a, US-02b, US-04, US-06a, US-03, US-06b |
| FR-14 | Provide an incident timeline that reconstructs the complete request-to-outcome path. | US-06b |
| FR-15 | Provide a dashboard showing recent actions, risk scores, incidents, approvals, blocked actions, agent status, and service health. | US-06b, US-22, US-09 |
| FR-16 | Allow authorized administrators to register, enable, disable, or quarantine an agent. | US-05, US-08 (Should) |
| FR-17 | Allow administrators to create/version policy bundles and simulate proposed policies against stored synthetic events before activation. | US-02a, US-07 (Should), US-08 (Should) |
| FR-18 | Apply rate/velocity controls for selected actions and agents. | US-04, US-05 |
| FR-19 | Expose service health, readiness, metrics, logs, and distributed trace identifiers. | US-20, US-23, US-09 |
| FR-20 | Support notification of critical incidents and pending approvals through the dashboard and optional demo email/webhook adapter. | US-05, US-22, US-30 (Could) |

### Non-functional requirements to stories

| NFR | Quality | Requirement | Delivered or verified by |
|---|---|---|---|
| NFR-01 | Security | Deny by default for unrecognized high-impact actions; blocked actions must never reach the protected API. | US-18, US-01, US-02a, US-02b, US-03, US-05, US-23, US-25, US-29, US-08 (Should) |
| NFR-02 | Performance | Target p95 governance latency <= 300 ms for the non-generative decision path under the agreed demo load; RAG explanation may execute asynchronously and target <= 3 seconds. | US-18, US-04, US-06a, US-27 |
| NFR-03 | Reliability | 100% of clearly blocked test actions must be prevented from reaching protected demo APIs; decisions must be idempotent for repeated correlation IDs. | US-18, US-01, US-02a, US-02b, US-04, US-05, US-26 |
| NFR-04 | Availability | Critical stateless services shall use health/readiness probes and restart/self-heal under the Kubernetes profile; public demo target availability during final validation >= 99%. | US-23, US-11a, US-09, US-27 |
| NFR-05 | Scalability | Demonstrate horizontal scaling for at least one stateless service and maintain acceptable latency under a defined load test. | US-23, US-27 |
| NFR-06 | Auditability | Every evaluated action shall have a correlation ID and a complete audit record; target audit completeness = 100% in evaluation scenarios. | US-18, US-01, US-19, US-02b, US-04, US-03, US-05, US-06b, US-26 |
| NFR-07 | Explainability | Target >= 90% of sampled generated explanations to cite the correct policy section(s) supporting the actual decision. | US-06a, US-26 |
| NFR-08 | Privacy | Use synthetic data only; no real customer personally identifiable information (PII) or financial data shall be stored or transmitted. | US-15, US-16, US-21 |
| NFR-09 | Maintainability | Critical services shall have automated tests and documented module/API boundaries; target >= 80% coverage for security-critical Python modules where practical. | US-13, US-10, US-07 (Should), US-08 (Should) |
| NFR-10 | Portability | All deployable services shall be containerized; the repository shall include local Docker Compose and Kubernetes deployment profiles. | US-16, US-20, US-23 |
| NFR-11 | Observability | Metrics, logs, and traces shall expose latency, errors, traffic, saturation, decision counts, and security events. | US-06b, US-09 |
| NFR-12 | Usability | The dashboard shall present decisions and approval context in plain English and support basic keyboard navigation and readable contrast. | US-03, US-22, US-08 (Should), US-28 (Should) |
| NFR-13 | Recoverability | Database backups/export and reproducible deployment scripts shall permit restoration of the demo environment within a target of 30 minutes. | US-27 |
| NFR-14 | Reproducibility | A documented setup shall allow a grader to run tests and core scenarios from the repository using version-pinned dependencies and sample environment configuration. | US-13, US-10, US-17, US-20, US-21, US-11a, US-24, US-25, US-11b, US-07 (Should) |

### Use cases to stories

| Use case | Name | Stories |
|---|---|---|
| UC-01 | Allow safe customer lookup | US-16, US-17, US-18, US-01, US-19 |
| UC-02 | Block prompt-injected refund | US-02b, US-24, US-25 |
| UC-03 | Hold high-value refund | US-03 |
| UC-04 | Deny cross-customer access | US-01 |
| UC-05 | Block bulk export | US-02a |
| UC-06 | Detect behavioral anomaly | US-21, US-04, US-22 |
| UC-07 | Quarantine repeated violations | US-05, US-30 |
| UC-08 | Explain a decision | US-06a |
| UC-09 | Reconstruct incident | US-19, US-06b |
| UC-10 | Simulate a new policy | US-07 |
| UC-11 | Onboard an agent | US-08 |
| UC-12 | Monitor platform health | US-23, US-09, US-27 |

### Acceptance tests to stories

| Test | Scenario | Stories |
|---|---|---|
| AT-01 | Normal transaction lookup: ALLOW, correct data, complete audit (UC-01) | US-18, US-01, US-19, US-26 |
| AT-02 | Cross-customer lookup: BLOCK, bank API not called (UC-04) | US-01, US-26 |
| AT-03 | Bulk export: BLOCK by hard policy (UC-05) | US-02a, US-26 |
| AT-04 | Refund exactly at limit: outcome matches policy boundary (UC-03) | US-03 |
| AT-05 | Refund above limit: HUMAN_REVIEW, no execution before approval (UC-03) | US-03, US-26 |
| AT-06 | Prompt-injected destination: BLOCK or review per provenance rule (UC-02) | US-02b, US-26 |
| AT-07 | Unusual admin sequence: high risk, block or quarantine (UC-06) | US-04, US-26 |
| AT-08 | Repeated denied calls: QUARANTINE, later calls denied (UC-07) | US-05, US-26 |
| AT-09 | Policy explanation cites correct passage and cannot change the decision (UC-08) | US-06a, US-26 |
| AT-10 | Incident replay by correlation ID: full ordered timeline (UC-09) | US-06b, US-26 |
| AT-11 | Policy simulation: no production policy changed, diff report generated (UC-10) | US-07 |
| AT-12 | Gateway dependency failure: fail closed, event logged | US-02a, US-27 |
| AT-13 | Load test: p95 latency measured, no data corruption (UC-12) | US-27 |
| AT-14 | Kubernetes pod deletion: replica restored (UC-12) | US-23, US-27 |
| AT-15 | Rolling update: rollout succeeds, rollback available (UC-12) | US-23, US-27 |
