# Sprint 2 planning

**Date:** 23 November 2026  
**Attendees:** Olusanya Mafe, Siyabonga Jali  
**Sprint dates:** Monday 23 November to Sunday 13 December 2026 (three weeks)  
**Sprint goal:** OPA policy, data-origin checks, machine learning risk scoring and policy-cited explanations work together (milestone M3).  

Sprint 2 starts a week earlier than first planned. Every Sprint 1 story was merged by 18 November and accepted at the review on 19 November, so Sprint 1 now ends on 22 November. The end date stays at 13 December, which keeps milestone M3 and the rest of the calendar where they were.

What the goal means at the review on 13 December: Vera's scenarios run in the Docker Compose stack, and each layer of the decision shows up in the gateway's answer and in the audit trail.

- UC-05: the export of every customer record is denied by the OPA policy, and the bank API is not called (AT-03). The audit event records the policy version and the rule that matched.
- UC-02: the account number taken from the forwarded email is labelled untrusted, and the refund is blocked with UNTRUSTED_ORIGIN (AT-06). An amount taken from the email and paid into Avery's own account is blocked the same way.
- UC-06: five small refunds against one purchase each pass the rules on their own, and the risk engine stops the fifth (AT-07). The audit event records the model version and the risk score.
- A blocked decision has a plain-English explanation that cites at least one section of the bank's written policy (AT-09). With the language model unavailable, a fallback message is shown and the decision does not change.
- UC-06 moves from pending to active. UC-03 and UC-07 stay pending until approvals (US-03) and quarantine (US-05) arrive in Sprint 3.

Events: weekly scrums on Wednesday 25 November, 2 December and 9 December; backlog refinement for Sprint 3 on Thursday 3 December, because the first Thursday is Thanksgiving; review with recorded demo and retrospective on Sunday 13 December. Ceremony checklist: [#13](https://github.com/olumafecode/agentsentinel/issues/13).

## Capacity

| Person | Available days this sprint | Notes (holidays, exams, work travel) |
|---|---|---|
| Olusanya Mafe | 19 | Thanksgiving, 26 and 27 November |
| Siyabonga Jali | 19 | Thanksgiving, 26 and 27 November |

Previous sprint velocity: 29 points (Sprint 1, all six stories accepted). Planned this sprint: 34 points.

34 points is 5 more than Sprint 1, in a sprint one week longer. Sprint 1's work was all merged in its first three days, so we treat the third week as a buffer rather than room for more stories. We check progress at the 2 December scrum.

## Part 1: what we will deliver (sprint backlog)

| Story | Points | Why now |
|---|---|---|
| [#28](https://github.com/olumafecode/agentsentinel/issues/28) US-02a Block unsafe tool calls with versioned OPA policy | 5 | Turns Sprint 1's per-task tool list into versioned bank policy, and the other checks this sprint run through the same OPA client (FR-03, FR-04, FR-17; AT-03, AT-12) |
| [#29](https://github.com/olumafecode/agentsentinel/issues/29) US-02b Block refunds whose details came from untrusted content | 8 | Prompt injection is the main threat the project addresses, and the origin labels have travelled with every call since Sprint 1 (FR-05; AT-06) |
| [#30](https://github.com/olumafecode/agentsentinel/issues/30) US-21 Generate the labelled synthetic action dataset | 5 | The risk model cannot be trained without it, and the test set must be frozen before any tuning (FR-07; NFR-08, NFR-14) |
| [#31](https://github.com/olumafecode/agentsentinel/issues/31) US-04 Score suspicious actions and sequences | 8 | Catches sequences in which every single call looks valid, which rules alone miss (FR-07, FR-18; AT-07) |
| [#32](https://github.com/olumafecode/agentsentinel/issues/32) US-06a Explain blocked and held decisions with policy citations | 8 | Auditors need the reason for a block in plain English, tied to the bank's written policy (FR-12; AT-09) |
| **Total** | **34** | |

Stories considered but not taken, and why:

- US-03 (hold large refunds for human approval): stays in Sprint 3. If we are ahead at the 2 December scrum, we start it early, because UC-03 is the next pending scenario.
- US-05 (quarantine after repeated violations): stays in Sprint 3 with US-03. Both change what happens after a decision, not how the decision is made.

## Part 2: how we will deliver it (tasks and owners)

Tasks were created with `plan-sprint` on 23 November and are assigned on the board. Sprint 1's two-track plan did not hold (Sprint 1 retrospective), so this time the owners are the people who will actually do the work. Olusanya builds. Siyabonga writes the bank's policy documents, checks the dataset sample by hand, reviews every pull request and accepts each story. Week 1 does the work that other stories wait for: the OPA client, the dataset and the policy documents.

The issue links in this table are filled in by `tools/board/link_tasks.py`, which also assigns each task to its owner on the board.

| Story | Task | Owner | Week |
|---|---|---|---|
| US-02a | [#143](https://github.com/olumafecode/agentsentinel/issues/143) US-02a.1 Rego policies: task-to-tool permissions, bulk export deny, value ranges, refund threshold | Olusanya Mafe | 1 |
| US-02a | [#144](https://github.com/olumafecode/agentsentinel/issues/144) US-02a.2 OPA container and gateway client with timeout and fail-closed handling | Olusanya Mafe | 1 |
| US-02a | [#145](https://github.com/olumafecode/agentsentinel/issues/145) US-02a.3 Policy unit tests with opa test, including boundary values | Olusanya Mafe | 1 |
| US-02a | [#146](https://github.com/olumafecode/agentsentinel/issues/146) US-02a.4 Versioned policy bundles; record policy_version in decisions and audit | Olusanya Mafe | 1 |
| US-02a | [#147](https://github.com/olumafecode/agentsentinel/issues/147) US-02a.5 Integration test AT-03 | Olusanya Mafe | 1 |
| US-21 | [#153](https://github.com/olumafecode/agentsentinel/issues/153) US-21.1 Event and sequence generator for normal behavior and the five failure modes | Olusanya Mafe | 1 |
| US-21 | [#154](https://github.com/olumafecode/agentsentinel/issues/154) US-21.2 Apply the labelling rules in code and review a 50-event sample by hand | Siyabonga Jali | 1 |
| US-21 | [#155](https://github.com/olumafecode/agentsentinel/issues/155) US-21.3 70/15/15 split with a frozen test set and checksums | Olusanya Mafe | 1 |
| US-21 | [#156](https://github.com/olumafecode/agentsentinel/issues/156) US-21.4 Dataset card: version, size, class balance, known limitations | Olusanya Mafe | 1 |
| US-06a | [#162](https://github.com/olumafecode/agentsentinel/issues/162) US-06a.1 Write the four synthetic bank policy documents with section IDs | Siyabonga Jali | 1 |
| US-02b | [#151](https://github.com/olumafecode/agentsentinel/issues/151) US-02b.4 Poisoned email and document fixtures | Olusanya Mafe | 1 |
| US-02b | [#148](https://github.com/olumafecode/agentsentinel/issues/148) US-02b.1 Data-origin labels on Vera's context: trusted user input versus retrieved content | Olusanya Mafe | 2 |
| US-02b | [#149](https://github.com/olumafecode/agentsentinel/issues/149) US-02b.2 Value-matching tracker for configured sensitive parameters | Olusanya Mafe | 2 |
| US-02b | [#150](https://github.com/olumafecode/agentsentinel/issues/150) US-02b.3 Rego rule for untrusted sensitive parameters | Olusanya Mafe | 2 |
| US-02b | [#152](https://github.com/olumafecode/agentsentinel/issues/152) US-02b.5 Scenario test AT-06 with a bank API call counter | Olusanya Mafe | 2 |
| US-04 | [#157](https://github.com/olumafecode/agentsentinel/issues/157) US-04.1 Feature pipeline for the six feature families in proposal Section 8.1 | Olusanya Mafe | 2 |
| US-04 | [#158](https://github.com/olumafecode/agentsentinel/issues/158) US-04.2 Train a Logistic Regression baseline and a Random Forest or gradient boosting comparator; check Isolation Forest | Olusanya Mafe | 2 |
| US-04 | [#159](https://github.com/olumafecode/agentsentinel/issues/159) US-04.3 Risk engine service POST /score returning score, band and model_version | Olusanya Mafe | 2 |
| US-06a | [#163](https://github.com/olumafecode/agentsentinel/issues/163) US-06a.2 Chunk and embed the policies into pgvector | Olusanya Mafe | 2 |
| US-04 | [#160](https://github.com/olumafecode/agentsentinel/issues/160) US-04.4 Gateway integration with precedence rules and velocity limits (FR-18) | Olusanya Mafe | 3 |
| US-04 | [#161](https://github.com/olumafecode/agentsentinel/issues/161) US-04.5 Evaluation notebook on the validation set | Olusanya Mafe | 3 |
| US-06a | [#164](https://github.com/olumafecode/agentsentinel/issues/164) US-06a.3 RAG service POST /explain with a provider-neutral LLM adapter and mock fallback | Olusanya Mafe | 3 |
| US-06a | [#165](https://github.com/olumafecode/agentsentinel/issues/165) US-06a.4 Validate citations against the retrieved set | Olusanya Mafe | 3 |
| US-06a | [#166](https://github.com/olumafecode/agentsentinel/issues/166) US-06a.5 Call the explanation service after the decision and store ExplanationEvidence | Olusanya Mafe | 3 |

Changes from the suggested tasks:

- US-02a.2: the OPA container already runs in the Compose stack (US-20, PR #131), so this task is the gateway's OPA client with its timeout and fail-closed handling.
- US-21.2: the labelling rules are applied in code as part of the generator (US-21.1). Siyabonga's part is the hand check of 50 events.
- US-04.3 and US-06a.3 each add a new service, so each one includes its Dockerfile, `/healthz` and `/readyz`, a Compose health check and an entry in the Images workflow, as set up in US-20. Their request and response models go into `libs/sentinel-contracts` before the services, as in Sprint 1.
- No task titles were changed on the board.

## Risks and dependencies

| Risk or dependency | Effect | What we do |
|---|---|---|
| 34 points against Sprint 1's 29, with Thanksgiving in week 1 | We may not finish everything | The sprint has a third week as a buffer. Check at the 2 December scrum. If we are behind at the 9 December scrum, US-06a ships on the mock language model and the live provider moves to Sprint 3 |
| US-02b, US-04 and US-06a are at the 8-point limit | One of them may run over | For US-04, split the gateway integration and velocity limits (US-04.4) into their own story |
| US-02b needs US-02a's OPA client; US-04 needs US-21's frozen dataset; US-06a needs the four policy documents; US-21 reads the refund limits from US-02a's policy data | Later tasks wait on earlier ones | Week 1 builds the OPA client, the dataset and the policy documents first |
| The task-to-tool table moves from `tools.json` into Rego | A wrong mapping blocks or allows the wrong tools | Siyabonga confirms the table, and whether Vera may use `get_accounts`, before US-02a.1 starts |
| The risk model could be tuned on the test set by mistake | The reported results would be too optimistic | The test set's checksum is recorded before any tuning, and the evaluation notebook reads only the validation set |
| The language model key is a secret, and the repository is public | The key could leak, or spending could run away | The key stays in `.env`, which git ignores. A monthly spend cap is set with the provider. CI and the recorded demo use the mock (ADR-007) |
| Two new services make the Compose stack bigger and CI slower | A red stack job blocks every merge | Each new service follows the US-20 pattern, and the stack job is a required check on `main` (Sprint 1 retrospective) |
| Machine learning libraries make the risk engine image larger | Slower builds and more findings in the Trivy scan | Pin versions, use the slim base image, and keep the scan at CRITICAL |
| `docker compose build` on Windows can fail with an `fs.read` permissions error (a Docker Compose bug) | Local builds stop | Update Docker Desktop. Until the fix arrives, set `$env:BUILDX_BAKE_ENTITLEMENTS_FS = "0"` in the PowerShell window before building |
| Sprint 1 stories were closed without a visible acceptance (Sprint 1 retrospective) | Unclear what the Product Owner accepted | A story is closed only after Siyabonga accepts it, with a closing comment that says so |

## Checklist

- [ ] Every selected story meets the Definition of Ready (checked at the refinement on 19 November)
- [ ] Every task has an owner
- [ ] Ceremony checklist for this sprint moved to In progress
- [ ] Siyabonga has confirmed the task-to-tool table before US-02a.1 starts
