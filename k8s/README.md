# Kubernetes profile

The manifests or Helm chart that run AgentSentinel on a local Kubernetes cluster (kind or k3d) to demonstrate self-healing, scaling, rolling updates and network controls.

| | |
|---|---|
| First built in | Sprint 3 |
| Stories | US-23, US-09 |
| Requirements | FR-09, FR-19; NFR-01, NFR-04, NFR-05, NFR-10 |

## What belongs here

- Deployments, Services, ConfigMaps, Secrets templates, probes, NetworkPolicy and the Horizontal Pod Autoscaler
- The cluster setup script and the rolling update script

## Rules for this folder

- Never commit a real Secret. `.gitignore` already blocks `k8s/**/secret*.yaml`.
- NetworkPolicy must stop the agent from reaching the bank API directly.

Status: placeholder created in Sprint 0 (US-13.3). Replace this line when the first code lands.
