# AgentSentinel threat model

This is the security baseline for the capstone (story US-14, milestone M1). It restates Section 9 of the approved proposal and links every threat to the control that answers it, the story that builds the control and the test that proves it. Review it at each sprint review when a story touched a trust boundary, and again after the bypass tests in US-29.

## 1. What we are protecting

| Asset | Why it matters |
|---|---|
| Customer money | A wrong or hijacked refund moves funds to the wrong place |
| Customer records | Cross-customer access or bulk export exposes personal data |
| The decision path | If the gateway can be skipped, no other control counts |
| Policy, model and threshold settings | Whoever changes them changes what the agent is allowed to do |
| The audit trail | It is the evidence for every decision; if it can be altered, nothing can be proven |
| Secrets | Signing keys, database credentials and LLM API keys |

All data is synthetic, so no real person or real money is exposed. The threats are modeled as if the data were real, because that is the situation the design is meant for.

## 2. Starting assumption

The AI agent may be mistaken, manipulated or compromised. Nothing the agent says about itself, its task or its permissions is trusted. Enforcement sits outside the model and uses credentials the agent cannot reach. The trust boundaries are drawn in [architecture.md, section 7](architecture.md#7-trust-boundaries).

| Zone | Contains | Trust |
|---|---|---|
| Untrusted | Customer input, emails and documents, Vera, LLM output | None. Treated as possibly wrong or hostile |
| Control | Sentinel Gateway, OPA, risk engine, approval service, audit service | Trusted to decide and enforce; changes need review |
| Protected | Demo bank tool APIs, bank data, audit store | Reachable only through the gateway |
| People | Approvers, analysts, administrators | Authenticated and limited by role; maker-checker for approvals |

## 3. Threats and controls

The threat list is the one in proposal Section 9.1. STRIDE categories are added to show coverage: Spoofing, Tampering, Repudiation, Information disclosure, Denial of service and Elevation of privilege.

| ID | Threat | STRIDE | Example | Controls | Built in | Proven by |
|---|---|---|---|---|---|---|
| T-01 | Agent goal hijack or prompt injection | Tampering, Elevation of privilege | A support email carries hidden instructions to refund an attacker's account | Data-origin labels, separation of trusted intent from retrieved content, hard policy, risk scoring, blocked side effects | US-02b, US-04, US-18 | AT-06; AgentDojo runs (US-25) |
| T-02 | Tool misuse | Tampering, Elevation of privilege | The agent calls close-account in place of close-dispute, or sends a negative refund | Per-task tool allowlist, schema and range validation, policy as code, least privilege | US-01, US-02a | AT-03; policy unit tests |
| T-03 | Identity or privilege abuse | Spoofing, Elevation of privilege | While serving Customer A, the agent requests Customer B's records | Agent registry, binding of user, session and customer, short-lived identity claims, no broad bank credential held by the agent | US-18, US-01, US-08 | AT-02 |
| T-04 | Sensitive data exfiltration | Information disclosure | The agent asks to export every customer record | Bulk export denial, destination controls, provenance checks, NetworkPolicy in the Kubernetes profile | US-02a, US-02b, US-23 | AT-03; bypass test (US-29) |
| T-05 | Runaway or repeated actions | Denial of service | Hundreds of small refunds, or repeated probing of admin tools | Velocity limits, anomaly detection, rate limiting, circuit breaker, quarantine and kill switch | US-04, US-05 | AT-07, AT-08 |
| T-06 | Policy bypass | Elevation of privilege | The agent, or anyone on the network, calls the bank API directly | Bank tools accept only requests with a gateway-signed single-use token; NetworkPolicy removes the direct path in the Kubernetes profile | US-18, US-23, US-29 | Token replay and expiry tests; NetworkPolicy bypass test |
| T-07 | Audit tampering | Tampering, Repudiation | An event is edited or deleted to hide an action | Append-only writes, a database role that cannot update or delete audit rows, hash-linked event chain, backup and export | US-19, US-27, US-29 | Tamper test; AT-10 |
| T-08 | Hallucinated explanation | Tampering, Repudiation | The explanation cites a policy that does not say what is claimed | Explanation generated only after the decision; citations checked against retrieved text; explanation cannot change the outcome; hand review of a sample | US-06a, US-26 | AT-09; citation review (NFR-07) |
| T-09 | Service failure | Denial of service | OPA or the risk engine is down during a high-impact action | Fail closed for high-risk actions, timeouts, health probes, retries where safe, Kubernetes restart and self-healing | US-02a, US-23, US-27 | AT-12, AT-14, AT-15 |
| T-10 | Secret leakage | Information disclosure | An API key is committed to the public repository | Secrets in environment or platform secret stores, GitHub secret scanning and push protection, no credentials in the repository, minimum scopes | US-13, US-10, US-11a | Secret scanning on; CI scans |

## 4. Link to recognized agentic risks

The proposal draws its threat catalog from the OWASP Top 10 for Agentic Applications. The mapping below is the team's reading; confirm the identifiers against the published list before quoting them in the final report.

| Threat | OWASP agentic risk |
|---|---|
| T-01 | ASI01 Agent Goal Hijack |
| T-02 | ASI02 Tool Misuse |
| T-03 | ASI03 Identity and Privilege Abuse |
| T-05 | ASI08 Cascading Failures, ASI10 Rogue Agents |

Governance is informed by the NIST AI Risk Management Framework and its Generative AI Profile. These sources guide engineering decisions; the capstone does not claim certification or regulatory compliance.

## 5. Security design principles

1. Deny by default for unknown sensitive actions.
2. Least privilege: the agent never receives unrestricted bank credentials.
3. Rules decide; AI advises. A model cannot override a deterministic deny.
4. Human judgment is mandatory for configured material actions.
5. Fail closed for high-impact decisions when a required security dependency is unavailable.
6. Every decision is observable and reconstructable.
7. The protected path must be non-bypassable in the reference architecture.
8. Policies, prompts, models and tool schemas are versioned artifacts.

## 6. What this model does not cover

Stating the limits is part of the model. These are outside the capstone release:

| Not covered | Why | What a real deployment would add |
|---|---|---|
| A compromised gateway host or a malicious administrator | The control zone is trusted in this prototype | Hardware-backed signing keys, separation of duties for administrators, independent log shipping |
| Real identity and access management | Sessions and roles are simulated; enterprise single sign-on is a Won't-have item | Integration with the bank's identity provider |
| Software supply chain beyond scanning | CI runs dependency, secret and image scans only | Signed images, a software bill of materials, pinned base images with provenance |
| Network-level denial of service on the public demo | The hosting platform's defaults are relied on | A web application firewall and rate limiting at the edge |
| Bypass prevention at network level on the public demo | NetworkPolicy exists only in the Kubernetes profile; the public demo relies on token verification | Private networking with enforced egress rules |
| Attacks on the LLM provider | The LLM is an external service behind an adapter | Provider due diligence and contractual controls |

## 7. Keeping this current

- A story that changes a trust boundary, a credential, the token design or the audit store updates this file in the same pull request.
- A confirmed weakness found in US-29 is logged as a bug on the board and added here if it reveals a threat that is missing.
- New threats get the next ID. Existing IDs are never reused.
