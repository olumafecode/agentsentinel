# ADR-006: Dual deployment profile

| | |
|---|---|
| Status | Accepted |
| Date | 2026-11-10 (recorded in Sprint 0; decision taken in the approved proposal, Appendix F) |
| Deciders | Product Owner, Scrum Master, Code Owners |
| Requirements | NFR-04, NFR-05, NFR-10, NFR-14 |
| Stories | US-20, US-11a, US-23 |

## Context

The capstone needs a stable public URL for the grader and the final video, and it must demonstrate container orchestration: health probes, network controls, scaling, rolling updates and self-healing. A managed Kubernetes cluster that stays up for months is costly and risky on a student budget.

## Decision

- Two profiles are built from the same container images.
- The public demo runs on a container hosting platform (Railway or Render) and is deployed automatically from main. The platform is chosen in ADR-009 during Sprint 3.
- The Kubernetes profile runs locally on kind or k3d and demonstrates Deployments, Services, ConfigMaps, Secrets, probes, NetworkPolicy, the Horizontal Pod Autoscaler and rolling updates.
- The project never describes Railway or Render as Kubernetes.

## Alternatives considered

| Alternative | Outcome |
|---|---|
| Managed Kubernetes for the public demo | Rejected. Cost and operational risk are out of proportion to the benefit. |
| Public demo only | Rejected. It would leave no orchestration evidence. |
| Local Kubernetes only | Rejected. The grader needs a URL that works at any time. |

## Consequences

What we gain:

- A reliable public demo and real orchestration evidence.
- The same images run in both profiles, which shows portability (NFR-10).

What it costs:

- Two sets of deployment configuration to maintain.
- Network-level bypass prevention is shown only in the Kubernetes profile; the public demo relies on token verification.
- Recovery and scaling evidence comes from a local cluster, which the report must state plainly.
