# AgentSentinel requirements baseline

This is the agreed requirements baseline for the capstone (story US-14, milestone M1). It restates Sections 2 to 5 and Appendices C and D of the approved proposal in one place, with the same identifiers the Scrum board uses as labels. If this document and the proposal ever disagree, raise it with the Product Owner and record the decision under Change control.

| | |
|---|---|
| Version | 1.0 (Sprint 0 baseline) |
| Owner | Product Owner |
| Signed off | Sprint 0 review, 15 November 2026 (pending) |
| Related | [Product backlog and traceability](../agile/product-backlog.md), [Architecture](../architecture/architecture.md), [Threat model](../architecture/threat-model.md), [ADRs](../adr/README.md) |

## 1. Purpose and aim

AI agents can call powerful tools, and a valid login does not prove that every tool call is appropriate. AgentSentinel is a control layer that sits between an AI banking agent and the bank's tools. It checks each proposed action for permission and intent before it runs, keeps a person in control of high-stakes actions, and produces evidence that security, risk and audit teams can inspect.

**Aim:** to design, build, deploy and evaluate a cloud-native AI runtime governance platform that detects, explains and contains unsafe or unauthorized autonomous-agent actions in a simulated banking environment.

## 2. Scope

| In scope | Out of scope |
|---|---|
| Synthetic retail-banking customer service, refunds, records, policy lookup, tool calls, security incidents, human approval and audit | Real bank connectivity, real customer data, real money movement, production regulatory certification, or replacement of enterprise identity and security platforms |
| A representative AI agent (Vera) plus a runtime governance layer and security dashboard | A general-purpose autonomous bank or a complete core banking system |
| One primary risk model plus deterministic controls and RAG explanation | Training a foundation model or hosting a large LLM on the Kubernetes cluster |
| Public demo deployment plus a Kubernetes deployment profile | Claiming that Railway or Render is itself Kubernetes |

Won't have in this release: enterprise single sign-on, real bank connectors, advanced multi-agent control and real-time regulatory reporting.

## 3. Stakeholders

| Stakeholder | Primary need |
|---|---|
| Bank customer or employee | Fast, correct service without unsafe access to money or personal data |
| AI banking agent (Vera) | Clear tool boundaries and predictable decisions so legitimate tasks can complete |
| Security operations analyst | Visibility into high-risk behavior, blocked actions, suspicious sequences and incident evidence |
| Human approver or manager | Context-rich approval decisions for high-impact actions |
| AI or platform engineer | Configuration, deployment, policy management, monitoring, and model and policy version control |
| Compliance or audit reviewer | Traceability showing what the agent attempted, why a decision occurred, and which rule or policy applied |
| Product Owner | Prioritized business value, accepted user stories and scope control |
| Scrum Master and engineering team | A transparent backlog, a testable Definition of Done and an achievable delivery plan |

## 4. Failure modes the system must handle

| Failure mode | Banking example | Why ordinary controls can miss it |
|---|---|---|
| Prompt injection or goal hijack | A support email contains hidden instructions telling the agent to send a refund to an attacker-controlled account | The agent itself is authenticated; the malicious instruction arrives through content the agent is expected to read |
| Misunderstood instruction | A customer asks to update a mailing address, but the agent changes the password-reset email instead | The API call is valid, but it does not match the customer's intent |
| Wrong tool or invalid details | The agent calls close-account in place of close-dispute, or submits a negative or implausible refund value | A well-formed request can still be the wrong request |
| Outside authority or cross-customer access | While serving Customer A, the agent accesses Customer B or requests a bulk customer export | Broad service credentials may technically allow the call |
| Valid but unintended sequence | The agent issues hundreds of small refunds or repeatedly probes administrative tools | Each individual action may look acceptable; the sequence is abnormal |

## 5. Use cases

| ID | Use case | Expected outcome | Why it matters | Stories |
|---|---|---|---|---|
| UC-01 | Allow safe customer lookup | ALLOW | Proves normal work is not blocked. | US-16, US-17, US-18, US-01, US-19 |
| UC-02 | Block prompt-injected refund | BLOCK | Demonstrates data provenance and prompt-injection resistance. | US-02b, US-24, US-25 |
| UC-03 | Hold high-value refund | HUMAN_REVIEW | Demonstrates human-in-the-loop control. | US-03 |
| UC-04 | Deny cross-customer access | BLOCK | Demonstrates session and customer boundary enforcement. | US-01 |
| UC-05 | Block bulk export | BLOCK | Demonstrates privilege and data-loss prevention. | US-02a |
| UC-06 | Detect behavioral anomaly | BLOCK or QUARANTINE | Demonstrates machine learning and anomaly detection beyond static rules. | US-21, US-04, US-22 |
| UC-07 | Quarantine repeated violations | QUARANTINE | Demonstrates containment and the kill switch. | US-05, US-30 (Could) |
| UC-08 | Explain a decision | EXPLAIN | Demonstrates policy-grounded RAG with citations. | US-06a |
| UC-09 | Reconstruct incident | AUDIT | Demonstrates end-to-end traceability. | US-19, US-06b |
| UC-10 | Simulate a new policy | SIMULATE | Demonstrates safe policy change management. | US-07 (Should) |
| UC-11 | Onboard an agent | CONFIGURE | Demonstrates manageable least-privilege setup. | US-08 (Should) |
| UC-12 | Monitor platform health | MONITOR | Demonstrates production engineering and observability. | US-23, US-09, US-27 |

### UC-01 Allow safe customer lookup

- **Scenario:** Customer asks for recent transactions; the request is scoped to that customer.
- **Actor:** Bank customer, through Vera
- **Starting point:** Customer is signed in; the session is bound to that customer.
- **Expected outcome:** ALLOW
- **Main flow:**
  1. Customer asks Vera for recent transactions.
  2. Vera proposes `get_transactions` for the session's customer.
  3. The gateway checks identity, tool permission, details and bank policy; all pass and risk is low.
  4. The gateway forwards the call with a signed single-use token and returns the data.
  5. One audit event records the full decision.
- **Functional requirements:** FR-01, FR-02, FR-03, FR-04, FR-06, FR-08, FR-13, FR-15
- **Non-functional requirements:** NFR-01, NFR-02, NFR-06
- **Acceptance evidence:** End-to-end safe lookup; policy allow; audit completeness (AT-01)
- **Stories:** US-16, US-17, US-18, US-01, US-19

### UC-02 Block prompt-injected refund

- **Scenario:** An untrusted email or document supplies an attacker-controlled refund destination.
- **Actor:** Attacker, through content Vera reads
- **Starting point:** Vera is handling a refund and reads an email or document that contains hidden instructions.
- **Expected outcome:** BLOCK
- **Main flow:**
  1. Vera reads the poisoned content and proposes a refund to the attacker's account.
  2. The gateway sees that the destination or amount came from untrusted content, not from the customer.
  3. Bank policy denies sensitive parameters from untrusted origins; the decision is BLOCK.
  4. The bank API is never called.
  5. The event is audited and an explanation cites the policy.
- **Functional requirements:** FR-01, FR-03, FR-04, FR-05, FR-06, FR-07, FR-08, FR-09, FR-12, FR-13
- **Non-functional requirements:** NFR-01, NFR-03, NFR-06, NFR-07
- **Acceptance evidence:** Prompt-injection scenario; provenance test; API not reached (AT-06)
- **Stories:** US-02b, US-24, US-25

### UC-03 Hold high-value refund

- **Scenario:** A refund exceeds the agent's automatic authority.
- **Actor:** Bank customer, Vera and a human approver
- **Starting point:** The refund is otherwise valid and requested by the customer.
- **Expected outcome:** HUMAN_REVIEW
- **Main flow:**
  1. Vera proposes a refund above the automatic limit.
  2. The gateway holds the action and creates an approval request.
  3. The approver sees the request, amount, reason, risk score and relevant policy in plain English.
  4. The approver approves or rejects; an unauthorized approver is refused.
  5. The held action resumes or ends under the same correlation ID, and the outcome is audited.
- **Functional requirements:** FR-01, FR-04, FR-06, FR-08, FR-10, FR-11, FR-12, FR-13, FR-15
- **Non-functional requirements:** NFR-01, NFR-02, NFR-06, NFR-12
- **Acceptance evidence:** Approval flow end to end; unauthorized approver denied; outcome audited (AT-04, AT-05)
- **Stories:** US-03

### UC-04 Deny cross-customer access

- **Scenario:** The agent serving Customer A requests Customer B's records.
- **Actor:** Vera (mistaken or manipulated)
- **Starting point:** The session is bound to Customer A.
- **Expected outcome:** BLOCK
- **Main flow:**
  1. Vera proposes a lookup for Customer B.
  2. The gateway compares the target with the session's customer scope.
  3. The decision is BLOCK and the bank API receives no call.
  4. The event is audited.
- **Functional requirements:** FR-02, FR-03, FR-06, FR-08, FR-09, FR-13
- **Non-functional requirements:** NFR-01, NFR-03, NFR-06
- **Acceptance evidence:** Session and customer binding test; denied downstream call (AT-02)
- **Stories:** US-01

### UC-05 Block bulk export

- **Scenario:** The agent requests an export of all customer records.
- **Actor:** Vera (mistaken or manipulated)
- **Starting point:** Vera has a customer-service role.
- **Expected outcome:** BLOCK
- **Main flow:**
  1. Vera proposes `export_customers`.
  2. Bank policy denies bulk export for this role and task.
  3. The decision is BLOCK and the bank API is not called.
  4. The policy version and matched rule are audited.
- **Functional requirements:** FR-03, FR-06, FR-08, FR-09, FR-13
- **Non-functional requirements:** NFR-01, NFR-03, NFR-06
- **Acceptance evidence:** Policy deny boundary test; blocked export integration test (AT-03)
- **Stories:** US-02a

### UC-06 Detect behavioral anomaly

- **Scenario:** The agent suddenly requests unusual admin tools after normal customer-service actions.
- **Actor:** Vera (compromised or misbehaving)
- **Starting point:** Earlier actions in the session were normal.
- **Expected outcome:** BLOCK or QUARANTINE
- **Main flow:**
  1. Vera proposes a run of actions that are unusual as a sequence.
  2. The risk engine scores the action and its recent history.
  3. A high score escalates the decision according to policy.
  4. The score, model version and decision are audited and shown on the dashboard.
- **Functional requirements:** FR-07, FR-08, FR-09, FR-13, FR-15, FR-18
- **Non-functional requirements:** NFR-02, NFR-03, NFR-06
- **Acceptance evidence:** Held-out sequence evaluation; false positive and recall metrics (AT-07)
- **Stories:** US-21, US-04, US-22

### UC-07 Quarantine repeated violations

- **Scenario:** The agent repeatedly attempts prohibited actions.
- **Actor:** Vera (compromised), security analyst
- **Starting point:** The agent has already had actions blocked inside the configured window.
- **Expected outcome:** QUARANTINE
- **Main flow:**
  1. Vera attempts a third prohibited action inside the window.
  2. The gateway quarantines the agent and denies the action.
  3. Every later action by that agent is denied.
  4. A critical incident and notification appear on the dashboard.
  5. An administrator can release the agent; the release is audited.
- **Functional requirements:** FR-07, FR-08, FR-09, FR-16, FR-18, FR-20
- **Non-functional requirements:** NFR-01, NFR-03, NFR-04, NFR-06
- **Acceptance evidence:** Velocity and quarantine scenario; subsequent actions denied (AT-08)
- **Stories:** US-05, US-30 (Could)

### UC-08 Explain a decision

- **Scenario:** An analyst asks why an action was blocked or escalated.
- **Actor:** Security analyst or auditor
- **Starting point:** A decision has been made and audited.
- **Expected outcome:** EXPLAIN
- **Main flow:**
  1. The analyst opens a blocked or held event.
  2. The RAG service retrieves relevant bank policy passages.
  3. It writes a plain-English explanation that cites policy section IDs.
  4. Citations are checked against the retrieved text; the explanation cannot change the decision.
- **Functional requirements:** FR-12, FR-13, FR-15
- **Non-functional requirements:** NFR-07, NFR-12
- **Acceptance evidence:** RAG grounding sample; correct policy citation rate (AT-09)
- **Stories:** US-06a

### UC-09 Reconstruct incident

- **Scenario:** A reviewer opens a prior incident and traces prompt, tool call, risk, policy, approval and outcome.
- **Actor:** Compliance or audit reviewer
- **Starting point:** The incident's events are in the audit trail.
- **Expected outcome:** AUDIT
- **Main flow:**
  1. The reviewer opens the incident by correlation ID.
  2. The timeline shows each step in order with its trace ID.
  3. The hash chain for those events verifies.
- **Functional requirements:** FR-13, FR-14, FR-15
- **Non-functional requirements:** NFR-06, NFR-11
- **Acceptance evidence:** Correlation ID audit replay; trace completeness (AT-10)
- **Stories:** US-19, US-06b

### UC-10 Simulate a new policy

- **Scenario:** An administrator tests a proposed policy on stored synthetic events before deployment.
- **Actor:** Administrator
- **Starting point:** A candidate policy bundle exists; stored events are available.
- **Expected outcome:** SIMULATE
- **Main flow:**
  1. The administrator runs the candidate bundle against stored events.
  2. A report lists the decisions that would change.
  3. The active policy is untouched until the administrator activates the new version.
- **Functional requirements:** FR-06, FR-17
- **Non-functional requirements:** NFR-09, NFR-14
- **Acceptance evidence:** Replay stored events; compare before and after policy outcomes (AT-11)
- **Stories:** US-07 (Should)

### UC-11 Onboard an agent

- **Scenario:** An administrator registers a new agent, role, tools, scopes and thresholds.
- **Actor:** Administrator or platform engineer
- **Starting point:** The administrator is signed in with the administrator role.
- **Expected outcome:** CONFIGURE
- **Main flow:**
  1. The administrator registers the agent with its role, allowed tools and thresholds.
  2. The gateway enforces the new settings straight away.
  3. A user without the administrator role is refused.
- **Functional requirements:** FR-02, FR-03, FR-16, FR-17
- **Non-functional requirements:** NFR-01, NFR-09, NFR-12
- **Acceptance evidence:** Admin authorization; new role and tool policy acceptance
- **Stories:** US-08 (Should)

### UC-12 Monitor platform health

- **Scenario:** An engineer reviews service health, latency, error rates, saturation and security event counts.
- **Actor:** AI or platform engineer
- **Starting point:** Services are running with telemetry enabled.
- **Expected outcome:** MONITOR
- **Main flow:**
  1. The engineer opens the metrics dashboard.
  2. Request rate, errors, p95 latency, saturation and decision counts are visible.
  3. A deleted pod is replaced and a rolling update completes while the service stays available.
- **Functional requirements:** FR-19, FR-15
- **Non-functional requirements:** NFR-04, NFR-05, NFR-11
- **Acceptance evidence:** Telemetry check; load test; pod recovery demonstration (AT-13, AT-14, AT-15)
- **Stories:** US-23, US-09, US-27

## 6. Functional requirements

The system shall:

| ID | Requirement | Priority | Delivered by |
|---|---|---|---|
| FR-01 | Intercept every protected tool/API call before execution. | Must | US-17, US-18, US-24 |
| FR-02 | Authenticate/identify the agent and bind the action to user, session, task, and correlation context. | Must | US-18, US-01, US-08 (Should) |
| FR-03 | Enforce task/tool permissions and least-privilege scopes. | Must | US-01, US-02a, US-08 (Should) |
| FR-04 | Validate structured action details such as amount, account identifier, target resource, and allowed value ranges. | Must | US-02a, US-03 |
| FR-05 | Record data provenance for configured sensitive parameters and distinguish trusted user intent from untrusted retrieved content. | Must | US-02b |
| FR-06 | Evaluate deterministic bank policy using Open Policy Agent or an equivalent policy engine. | Must | US-02a, US-02b, US-07 (Should) |
| FR-07 | Calculate a configurable machine-learning risk/anomaly score for selected actions and short action sequences. | Must | US-21, US-04 |
| FR-08 | Produce one enforceable decision: ALLOW, HUMAN_REVIEW, BLOCK, or QUARANTINE. | Must | US-18, US-01, US-02a, US-02b, US-04, US-03, US-05 |
| FR-09 | Prevent blocked/quarantined actions from reaching protected bank APIs. | Must | US-18, US-01, US-02a, US-02b, US-04, US-05, US-23, US-29 |
| FR-10 | Create approval requests for configured high-impact actions and allow authorized users to approve or reject them. | Must | US-03 |
| FR-11 | Resume or terminate the held action according to the approval outcome without losing audit context. | Must | US-03 |
| FR-12 | Provide a plain-English decision explanation grounded in retrieved policy evidence and citation identifiers. | Must | US-06a |
| FR-13 | Write an audit event for every evaluated action, including decision inputs, policy/model versions, risk result, final outcome, and timestamps. | Must | US-01, US-19, US-02a, US-02b, US-04, US-06a, US-03, US-06b |
| FR-14 | Provide an incident timeline that reconstructs the complete request-to-outcome path. | Must | US-06b |
| FR-15 | Provide a dashboard showing recent actions, risk scores, incidents, approvals, blocked actions, agent status, and service health. | Must | US-06b, US-22, US-09 |
| FR-16 | Allow authorized administrators to register, enable, disable, or quarantine an agent. | Must | US-05, US-08 (Should) |
| FR-17 | Allow administrators to create/version policy bundles and simulate proposed policies against stored synthetic events before activation. | Must | US-02a, US-07 (Should), US-08 (Should) |
| FR-18 | Apply rate/velocity controls for selected actions and agents. | Must | US-04, US-05 |
| FR-19 | Expose service health, readiness, metrics, logs, and distributed trace identifiers. | Must | US-20, US-23, US-09 |
| FR-20 | Support notification of critical incidents and pending approvals through the dashboard and optional demo email/webhook adapter. | Must | US-05, US-22, US-30 (Could) |

FR-17 has two parts. Versioning of policy bundles is Must-have and delivered by US-02a. Simulation of a proposed policy is Should-have (US-07) and is the first thing dropped if time runs short.

## 7. Non-functional requirements

| ID | Quality | Requirement or target | Delivered or verified by |
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

## 8. Decision outcomes and precedence

Every evaluated action ends in exactly one outcome (FR-08):

| Outcome | Meaning |
|---|---|
| ALLOW | The action runs. The gateway forwards it with a signed single-use token |
| HUMAN_REVIEW | The action is held until an authorized person approves or rejects it |
| BLOCK | The action is stopped and never reaches the bank API |
| QUARANTINE | The action is stopped and the agent is contained; all its later actions are denied until an administrator releases it |

Precedence: hard deny, then quarantine condition, then mandatory human-review rule, then risk-based escalation, then allow. The risk model can add caution but can never allow an action that a hard rule denies. A generated explanation can never change the outcome. If required context is missing for a high-impact action, the system fails closed or asks for human review.

## 9. Acceptance tests

| ID | Scenario | Input or trigger | Expected result | Use case | Stories |
|---|---|---|---|---|---|
| AT-01 | Normal transaction lookup | Customer A asks for own transactions. | ALLOW; correct data; complete audit. | UC-01 | US-18, US-01, US-19, US-26 |
| AT-02 | Cross-customer lookup | Customer A session requests Customer B. | BLOCK; bank API not called. | UC-04 | US-01, US-26 |
| AT-03 | Bulk export | Vera requests all customers. | BLOCK by hard policy. | UC-05 | US-02a, US-26 |
| AT-04 | Refund exactly at limit | Refund equals the configured automatic threshold. | Outcome matches the policy boundary specification. | UC-03 | US-03 |
| AT-05 | Refund above limit | Refund is above the threshold. | HUMAN_REVIEW; no execution before approval. | UC-03 | US-03, US-26 |
| AT-06 | Prompt-injected destination | Recipient or amount originates from an untrusted email or document. | BLOCK or review according to the configured provenance rule. | UC-02 | US-02b, US-26 |
| AT-07 | Unusual admin sequence | Normal service actions followed by admin credential or export requests. | High risk; block or quarantine. | UC-06 | US-04, US-26 |
| AT-08 | Repeated denied calls | Three or more prohibited calls in the window. | QUARANTINE; later calls denied. | UC-07 | US-05, US-26 |
| AT-09 | Policy explanation | Analyst opens a blocked event. | Explanation cites the correct policy passage and cannot change the decision. | UC-08 | US-06a, US-26 |
| AT-10 | Incident replay | Open a prior incident by correlation ID. | Full ordered timeline available. | UC-09 | US-06b, US-26 |
| AT-11 | Policy simulation | Run a proposed policy on stored events. | No production policy changed; difference report generated. | UC-10 | US-07 (Should) |
| AT-12 | Gateway dependency failure | OPA or the risk engine is unavailable during a sensitive call. | Fail closed according to the configured rule; event logged. | Cross-cutting | US-02a, US-27 |
| AT-13 | Load test | Defined concurrent sessions and requests. | p95 latency target measured; no data corruption. | UC-12 | US-27 |
| AT-14 | Kubernetes pod deletion | Delete one risk engine or gateway pod. | Deployment restores the desired replica; service remains or recovers quickly. | UC-12 | US-23, US-27 |
| AT-15 | Rolling update | Deploy a new risk engine image. | Rollout succeeds; health checks pass; rollback available. | UC-12 | US-23, US-27 |

## 10. Success targets

These are prototype targets from proposal Section 12, not results. The final report presents measured values and explains any target not met.

| Measure | Target |
|---|---|
| Unsafe-action recall | 90% or more on the held-out project scenario suite |
| Precision for unsafe or high-risk classification | 90% or more where machine learning classification applies |
| False block rate | Under 5% on benign scripted scenarios |
| Deterministic prohibited-action enforcement | 100% of explicitly denied policy cases blocked |
| Audit completeness | 100% of evaluated acceptance scenarios contain the required fields and a correlation ID |
| RAG citation correctness | 90% or more on sampled policy-explanation scenarios |
| p95 non-generative governance latency | 300 ms or less under the agreed demo load |
| Critical service automated tests | 80% code coverage or more where practical, with security-critical logic first |
| Kubernetes recovery demonstration | A deleted stateless pod is replaced without manual recreation |
| Rolling deployment demonstration | One service is updated while functional availability is maintained |
| CI quality gate | No merge to main when mandatory unit or policy tests fail |
| Public demo stability | All selected user stories operate correctly throughout the final presentation rehearsal |

## 11. Assumptions and constraints

- The handbook permits simulated data and a deployed web application on a suitable hosting environment.
- The team has access to GitHub, Docker, a local Kubernetes environment and at least one supported external LLM API, or a mock fallback.
- The final project is a prototype demonstrating engineering patterns, not a regulated production banking product.
- No real customer data, credentials, bank endpoints or real payments are used.
- Delivery runs from 9 November 2026 to 24 January 2027; the sprint calendar is in `docs/agile/sprint-calendar.md`.

## 12. Change control

New requests go to the product backlog and are prioritized by the Product Owner. Scope is not added during an active sprint unless the change fixes a critical defect or security blocker. A change to a requirement in this document needs a pull request, the Product Owner's approval and a row in the table below. Changes that affect security boundaries, persistence, external services or deployment also need an ADR.

| Date | Change | Reason | Approved by |
|---|---|---|---|
| 2026-11-10 | Baseline created from the approved proposal | Sprint 0, story US-14 | Pending sign-off |

