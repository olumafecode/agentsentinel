# AgentSentinel architecture

This is the design baseline for the capstone (story US-14, milestone M1). It restates Section 7 and Appendix E of the approved proposal, with diagrams that render on GitHub. Decisions and their reasons are in the [ADRs](../adr/README.md); threats and controls are in the [threat model](threat-model.md); requirement IDs are defined in the [requirements baseline](../requirements/requirements.md).

## 1. The idea in one paragraph

The AI agent proposes; AgentSentinel decides; a person decides when the risk needs human judgment. Vera, the banking agent, can never call a bank tool directly. Every protected action goes to the Sentinel Gateway, which checks who the agent is acting for, whether the tool is allowed, whether the details are sensible, what bank policy says, where sensitive values came from and how risky the behavior looks. Only an approved action reaches the bank, carrying a signed single-use token. Every decision is recorded in a tamper-evident audit trail and can be explained in plain English with policy citations.

## 2. System context

```mermaid
flowchart LR
    customer["Bank customer"] --> web["Demo bank web app"]
    web --> vera["Vera<br/>AI banking agent"]
    content["Emails and documents<br/>(untrusted content)"] -.-> vera
    vera -->|"proposes a tool call"| gw["AgentSentinel<br/>Sentinel Gateway"]
    gw -->|"approved calls only,<br/>signed single-use token"| bank["Demo bank tool APIs"]
    approver["Human approver"] --> dash["Security dashboard"]
    analyst["Security analyst<br/>or auditor"] --> dash
    admin["Administrator or<br/>platform engineer"] --> dash
    dash --> gw
    gw -.->|"explanation requests"| llm["External LLM<br/>through an adapter"]
    vera -.-> llm
```

The single arrow from the gateway to the bank APIs is the point of the design: there is no other path to a protected tool (ADR-001).

## 3. Logical architecture

```mermaid
flowchart TB
    client["Web / demo client"] --> agent["AI banking agent (Vera)"]
    agent --> gateway["Sentinel Gateway<br/>Policy Enforcement Point"]
    gateway --> bankapi["Demo bank tool APIs"]

    gateway --> opa["OPA policy service"]
    gateway --> risk["Risk engine<br/>machine learning inference"]
    gateway --> approval["Approval service"]
    gateway --> audit["Audit and incident service"]
    gateway -.->|"after the decision"| rag["RAG policy explanation"]

    risk --> pg[("PostgreSQL + pgvector")]
    approval --> pg
    audit --> pg
    rag --> pg
    rag -.-> llm["External LLM adapter"]

    dashboard["Security dashboard"] --> approval
    dashboard --> audit
    dashboard --> gateway

    otel["OpenTelemetry<br/>metrics, logs, traces"]
    gateway -.-> otel
    risk -.-> otel
    approval -.-> otel
    audit -.-> otel
```

Service boundaries exist only where security, scaling, testing or ownership differ. The proposal's diagram also shows a Redis cache or queue; it is optional and will be added only if velocity counters or asynchronous explanation need it.

## 4. Components

| Component | Responsibility | Technology direction | Repository folder |
|---|---|---|---|
| Demo bank web app | Presents customer-service scenarios and invokes Vera | React or lightweight web client | `apps/dashboard` (shared UI) |
| AI banking agent (Vera) | Plans tasks and proposes tool calls; never receives bank credentials | Python agent, provider-neutral LLM adapter | `apps/banking-agent` |
| Sentinel Gateway | Intercepts actions, assembles context, runs the checks, enforces the decision, signs approved requests | FastAPI, Python | `services/sentinel-gateway` |
| Identity and scope module | Binds agent, user, session, customer and task; validates tool scope | Gateway module, session claims | `services/sentinel-gateway` |
| Policy service | Evaluates deterministic rules: refund limits, bulk export ban, rate limits, task and tool permissions | Open Policy Agent, Rego | `policies/opa` |
| Provenance module | Tracks where configured action parameters came from | Structured labels on arguments | `services/sentinel-gateway` |
| Risk engine | Scores an action and its recent sequence | scikit-learn; Logistic Regression baseline, Random Forest or gradient boosting comparator | `services/risk-engine`, `ml/` |
| Approval service | Creates, authorizes, expires, approves or rejects held actions | FastAPI, PostgreSQL | `services/approval-service` |
| RAG explanation service | Retrieves policy passages and writes a plain-English explanation after the decision | Embeddings, pgvector, external LLM adapter | `services/rag-service` |
| Audit and incident service | Stores hash-linked events, correlation IDs, policy and model versions, incident timelines | PostgreSQL | `services/audit-service` |
| Dashboard | Shows actions, approvals, incidents, agent state and health | React or server-rendered UI | `apps/dashboard` |
| Demo bank API | Synthetic customers, accounts, transactions, refunds and admin tools; accepts only gateway-signed requests | FastAPI | `apps/demo-bank-api` |
| Observability | Metrics, logs and traces | OpenTelemetry; Prometheus and Grafana in the Kubernetes profile | `k8s/` |

## 5. The seven-step decision pipeline

```mermaid
flowchart TB
    start(["Vera proposes a protected action"]) --> s1
    s1["1. Identity and session<br/>Who is the agent acting for?"] --> s2
    s2["2. Tool permission<br/>Is this tool allowed for this task and role?"] --> s3
    s3["3. Input and details validation<br/>Are amounts, accounts, formats and limits sensible?"] --> s4
    s4["4. Bank policy as code<br/>Do hard rules permit the action?"] --> s5
    s5["5. Data origin (provenance)<br/>Did sensitive values come from trusted user intent<br/>or from untrusted content?"] --> s6
    s6["6. AI intent and behavior risk<br/>Does the action match the request and normal behavior?"] --> s7
    s7{"7. Decision and enforcement"}
    s7 -->|ALLOW| allow["Forward to the bank API<br/>with a signed single-use token"]
    s7 -->|HUMAN_REVIEW| review["Hold the action<br/>and ask an approver"]
    s7 -->|BLOCK| block["Stop the action"]
    s7 -->|QUARANTINE| quarantine["Stop the action<br/>and contain the agent"]
    s5 -. "any rule in steps 1 to 5 fails clearly: stop early" .-> block
    allow --> auditnode[("Audit event for every decision")]
    review --> auditnode
    block --> auditnode
    quarantine --> auditnode
```

Cheap deterministic checks run first. Steps 1 to 5 are rules; step 6 is the machine learning risk signal, which can add caution but cannot overturn a hard block (ADR-003).

**Decision precedence:** hard deny, then quarantine condition, then mandatory human-review rule, then risk-based escalation, then allow. If required context is missing for a high-impact action, or a security dependency such as OPA is down, the gateway fails closed or asks for human review; it never guesses.

## 6. What happens to one action

```mermaid
sequenceDiagram
    autonumber
    participant V as Vera
    participant G as Sentinel Gateway
    participant O as OPA
    participant R as Risk engine
    participant A as Approval service
    participant B as Demo bank API
    participant L as Audit service
    participant X as RAG explanation

    V->>G: ProtectedActionRequest (correlation ID, tool, arguments, origin labels)
    G->>G: Steps 1 to 3: identity, tool permission, details
    G->>O: Step 4 and 5: evaluate policy with origin labels
    O-->>G: PolicyDecision (version, matched rules)
    G->>R: Step 6: score action and recent sequence
    R-->>G: RiskAssessment (score, band, model version)
    alt ALLOW
        G->>B: Tool call with signed single-use token
        B-->>G: Result
        G-->>V: ALLOW and result
    else HUMAN_REVIEW
        G->>A: Create approval request
        G-->>V: HUMAN_REVIEW (held)
        A-->>G: Approved or rejected by an authorized person
        G->>B: Tool call with token, only if approved
    else BLOCK or QUARANTINE
        G-->>V: Refused with reason codes
    end
    G->>L: Hash-linked audit event (always)
    G-)X: Explain the decision (in the background)
    X-)L: ExplanationEvidence with policy citations
```

## 7. Trust boundaries

```mermaid
flowchart LR
    subgraph untrusted["Untrusted: may be wrong, manipulated or hostile"]
        user["Customer input"]
        docs["Emails and documents"]
        agentbox["Vera and the LLM's output"]
    end
    subgraph control["Control zone: AgentSentinel"]
        gw["Sentinel Gateway"]
        pol["OPA policy"]
        rk["Risk engine"]
        ap["Approval service"]
        au["Audit service"]
    end
    subgraph protected["Protected: reachable only through the gateway"]
        bank["Demo bank tool APIs"]
        db[("Bank data and audit trail")]
    end
    user --> agentbox
    docs --> agentbox
    agentbox -->|"proposals only, no credentials"| gw
    gw --> pol
    gw --> rk
    gw --> ap
    gw --> au
    gw -->|"signed single-use token"| bank
    bank --> db
    au --> db
```

The design assumes the agent may be mistaken, manipulated or compromised. Security-critical enforcement therefore sits outside the model and uses credentials the agent cannot reach.

## 8. Interface contracts

These are the minimum fields from proposal Appendix E. The Pydantic versions are built in story US-18; the stored entities are in [`data/synthetic/README.md`](../../data/synthetic/README.md).

| Contract | Minimum fields |
|---|---|
| ProtectedActionRequest | correlation_id, agent_id, user or session_id, customer_scope, task_type, tool_name, structured_arguments, provenance_labels, timestamp |
| PolicyDecision | policy_version, matched_rules, hard_decision, reasons |
| RiskAssessment | model_version, feature_schema_version, risk_score, risk_band, top contributing features where supported |
| GovernanceDecision | decision (ALLOW, HUMAN_REVIEW, BLOCK or QUARANTINE), reason_codes, approval_id if required, signed_execution_token if allowed |
| AuditEvent | correlation_id, event_type, actor, immutable timestamp, policy and model versions, decision or outcome, previous_event_hash, event_hash |
| ExplanationResponse | correlation_id, plain_english_reason, evidence_ids, policy sections, generated_at, model and provider version |

## 9. Architecture patterns

| Pattern | Where used | Reason |
|---|---|---|
| API Gateway and Policy Enforcement Point | Central interception boundary | Creates one enforceable path to protected tools |
| Policy as code | Bank business and security rules | Rules can be reviewed, versioned, unit-tested and deployed independently of prompts |
| Defense in depth | Rules, provenance, machine learning and human review | No single AI model is trusted as the only control |
| Maker-checker and human in the loop | High-value or unusual actions | Keeps human accountability for material decisions |
| Event-sourcing-style audit trail | Security decisions and incidents | Stores append-only events suitable for reconstruction |
| Circuit breaker and fail closed | Policy or risk dependency failure | High-impact actions stop when a security dependency fails |
| Repository pattern | Persistence access | Separates business logic from the PostgreSQL implementation |
| Adapter pattern | LLM, notification and model provider | Reduces vendor lock-in and makes testing easier |
| Dual deployment profile | Public demo and Kubernetes | A simple public deployment plus cloud-native orchestration evidence |

## 10. Deployment profiles

```mermaid
flowchart TB
    subgraph ci["GitHub Actions"]
        build["Lint, tests, scans,<br/>image build tagged with commit SHA"]
    end
    subgraph public["Profile 1: public demo (Railway or Render)"]
        pdash["Dashboard and public API"]
        psvc["Gateway, risk, approval, audit, RAG<br/>(private networking)"]
        pdb[("Managed PostgreSQL")]
        pdash --> psvc --> pdb
    end
    subgraph k8s["Profile 2: Kubernetes (kind or k3d)"]
        ing["Ingress"]
        dep["Deployments with readiness and liveness probes"]
        hpa["Horizontal Pod Autoscaler"]
        np["NetworkPolicy: agent may reach the gateway only"]
        cfg["ConfigMaps and Secrets"]
        ing --> dep
        hpa -.-> dep
        np -.-> dep
        cfg -.-> dep
    end
    build -->|"deploy on merge to main"| public
    build -->|"same images"| k8s
```

The public demo maximizes reliability for the grader. The Kubernetes profile demonstrates orchestration. The project does not claim that Railway or Render is Kubernetes (ADR-006).

| Kubernetes capability | Use in AgentSentinel |
|---|---|
| Deployments | Manage the stateless gateway, risk, RAG, approval, audit and dashboard workloads |
| Services | Stable internal discovery between components |
| ConfigMaps | Non-secret configuration such as thresholds and endpoint names |
| Secrets | API keys and credentials, kept out of source control |
| NetworkPolicy | Restrict unnecessary network paths; block the agent from reaching bank tools directly |
| Readiness and liveness probes | Remove unhealthy instances from traffic and restart failed workloads |
| Horizontal Pod Autoscaler | Scale a stateless service under load |
| Rolling updates | Deploy new versions gradually, with rollback |
| Resource requests and limits | Prevent uncontrolled CPU and memory use |
| Ingress | Expose only intended public entry points |

## 11. Design rules that every change must respect

1. Deny by default for unknown sensitive actions.
2. Least privilege: the agent never receives unrestricted bank credentials.
3. Rules decide; AI advises. A model cannot override a deterministic deny.
4. Human judgment is mandatory for configured material actions.
5. Fail closed for high-impact decisions when a required security dependency is unavailable.
6. Every decision is observable and reconstructable.
7. The protected path must be non-bypassable in the reference architecture.
8. Policies, prompts, models and tool schemas are versioned artifacts.

A change that touches any of these needs an ADR and a Code Owner review.
