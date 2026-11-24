# Synthetic bank policy documents

The fictional bank's written policies, which the explanation service retrieves and cites when it explains a blocked or held decision (US-06a, AT-09).

| | |
|---|---|
| First built in | Sprint 2 |
| Stories | US-06a (task US-06a.1, written by the Product Owner) |
| Requirements | FR-12; NFR-07, NFR-08 |

## The documents

| File | Document ID | What it covers |
|---|---|---|
| `ai-agent-access-policy.md` | AAP | Agent registration and identity, which tools each task allows, the gateway, instructions found in content, monitoring |
| `customer-data-access-policy.md` | CDA | Whose data an agent may use, bulk access, changing customer data, records |
| `refund-authorization-policy.md` | RAP | Conditions for a refund, the automatic limit and hard cap, approval, where refund details may come from, refund patterns |
| `incident-response-standard.md` | IRS | What counts as an incident, quarantine, the kill switch, freezing an account, evidence, recovery |

Veridane is fictional. The documents were written by the team for this project, and nothing in them is copied from a real bank's policy.

## Format

The explanation service splits each document into sections and cites them by ID, so the format is fixed:

- Each numbered part is a level-2 heading, such as `## 3. Amounts and limits`.
- Each citable section is a level-3 heading that starts with its ID, such as `### RAP-3.2 Refunds up to the automatic limit`. The ID is the document ID, the part number and the section number.
- A section is one to four short paragraphs, or a table. A section that refers to another names it by ID, such as "under IRS-3.1".

## Rules for this folder

- Section IDs never change once published, because stored explanations cite them. A section that no longer applies stays in place with its text replaced by "Withdrawn in version X.Y." and its heading kept.
- Every limit or list in a document must match the live policy in `policies/opa/agentsentinel/data.json` and the settings in `data/synthetic/labelling-rules.md`. `tests/test_policy_documents.py` fails if they differ, so a policy change updates all three in the same pull request.
- The Product Owner approves every change. A change raises the document's version and, if it changes a rule, the policy bundle's revision too.

## Which sections support which decision

The sections an explanation should cite for each reason code. This is also the answer key for the citation sample in NFR-07 and US-26.

| Reason code | Decision | Sections |
|---|---|---|
| `MISSING_CONTEXT` | BLOCK | AAP-2.3 |
| `IDENTITY_MISMATCH` | BLOCK | AAP-2.2, AAP-2.3 |
| `AGENT_DISABLED` | BLOCK | AAP-2.4, IRS-3.2 |
| `UNKNOWN_TOOL` | BLOCK | AAP-3.3 |
| `TOOL_NOT_ALLOWED` | BLOCK | AAP-3.1, AAP-3.2, AAP-3.4, RAP-2.1 |
| `OUTSIDE_CUSTOMER_SCOPE` | BLOCK | CDA-2.1, CDA-2.2, CDA-2.3, RAP-2.2 |
| `POLICY_DENY` | BLOCK | CDA-2.4, AAP-3.4 |
| `INVALID_ARGUMENTS` | BLOCK | AAP-4.4, RAP-3.1 |
| `STALE_REQUEST` | BLOCK | AAP-4.2 |
| `UNTRUSTED_ORIGIN` | BLOCK | AAP-5.1, AAP-5.2, RAP-5.1, RAP-5.2 |
| `REFUND_OVER_LIMIT` | HUMAN_REVIEW | RAP-3.3, RAP-4.1 |
| `REFUND_OVER_LIMIT` | BLOCK | RAP-3.4 |
| `HIGH_RISK` | BLOCK or HUMAN_REVIEW | AAP-6.1, AAP-6.2, RAP-6.1, RAP-6.2 |
| `REPEATED_VIOLATIONS` | QUARANTINE | IRS-3.1, AAP-6.3 |
| `AGENT_QUARANTINED` | QUARANTINE | IRS-3.1, IRS-6.1 |
| `DEPENDENCY_UNAVAILABLE` | BLOCK | AAP-4.3, IRS-3.4 |
| `APPROVED_BY_HUMAN` | ALLOW | RAP-4.1, RAP-4.3 |
| `REJECTED_BY_HUMAN` | BLOCK | RAP-4.1, RAP-4.3 |

`WITHIN_POLICY` needs no citation: allowed actions are not explained.

## Sections a later story puts into effect

The documents state the bank's whole policy. Some of it is enforced only once a later story is done; until then the gateway is stricter or does not yet check it.

| Sections | Put into effect by | Until then |
|---|---|---|
| AAP-5.2, RAP-5.1, RAP-5.2 | US-02b (Sprint 2) | A refund into another customer's account is already blocked under RAP-2.2 |
| AAP-6.1, AAP-6.2, RAP-6.1, RAP-6.2 | US-04 (Sprint 2) | Actions and sequences are not yet scored |
| IRS-5.3 | US-06a (Sprint 2) | No explanations are written yet |
| RAP-3.3, RAP-4.1, RAP-4.2, RAP-4.3, IRS-4.2 | US-03 (Sprint 3) | A refund above 200.00 USD is blocked instead of held |
| AAP-6.3, IRS-3.1, IRS-3.2, IRS-6.1 | US-05 (Sprint 3) | Agents are not quarantined automatically |
| IRS-4.1 | US-05 and US-22 (Sprint 3) | There is no security dashboard yet |
| IRS-5.2 | US-06b (Sprint 3) | `verify-chain` and the audit tables are the evidence |
