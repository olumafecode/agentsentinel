# Incident Response Standard

| | |
|---|---|
| Document ID | IRS |
| Version | 1.0 |
| Owner | Head of Security Operations, Veridane |
| Effective from | 1 December 2026 |
| Next review | 1 December 2027 |

Veridane is a fictional bank. This standard was written for the AgentSentinel project and describes no real bank.

## 1. Purpose and scope

### IRS-1.1 Purpose

This standard sets out how Veridane detects, contains and investigates incidents involving AI agents that act for customers, so that harm is stopped quickly and every incident can be reconstructed afterwards.

### IRS-1.2 Scope

This standard covers incidents in which an AI agent proposes an action that is prohibited, manipulated or abnormal, incidents in which a control that governs agents fails, and suspected fraud reported to an agent by a customer.

## 2. Recognizing an incident

### IRS-2.1 What counts as an incident

The following are incidents: a quarantined agent; an action blocked because its details came from untrusted content; an attempt to reach another customer's data or to export customer records; an abnormal sequence of actions; a control that could not run; and a customer reporting a transaction they do not recognize.

### IRS-2.2 Severity

An incident is critical when an agent is quarantined or a customer reports suspected fraud. It is high when an action is blocked for untrusted content, for another customer's data or for a bulk export. Every other incident is medium. The severity sets how quickly the security team must respond under IRS-4.1.

## 3. Containment

### IRS-3.1 Quarantine after repeated violations

An agent that has three actions blocked within ten minutes is quarantined at once. The action that triggers the quarantine is stopped, and every later action by that agent is refused until an administrator releases it under IRS-6.1.

### IRS-3.2 Stopping an agent at once

An administrator may quarantine or disable any agent at any time, without waiting for it to break a rule. This is the kill switch. Its use is recorded.

### IRS-3.3 Freezing an account on suspected fraud

When a customer reports a transaction they do not recognize, the account is frozen first so that no further money can leave it, and investigated second. An AI agent may freeze the account during a dispute, as AAP-3.5 allows.

### IRS-3.4 When a control fails

If a control that judges agent actions is unavailable, actions are blocked until it returns, as AAP-4.3 requires. The failure is logged and treated as an incident.

## 4. Notification

### IRS-4.1 Raising the alarm

A critical incident appears on the security dashboard with a notification as soon as it is raised. The security team acknowledges a critical incident within 15 minutes and a high one within 4 hours, during staffed hours.

### IRS-4.2 Pending approvals

Refunds held for approval under RAP-3.3 are shown to approvers on the dashboard, so that a customer is not left waiting without anyone knowing.

## 5. Evidence and investigation

### IRS-5.1 The audit trail is the evidence

Every action an agent proposes is recorded with a correlation ID, from the request to the decision and its outcome. The records are append-only and linked by hashes, so that any change can be detected.

### IRS-5.2 Reconstructing an incident

An investigator opens an incident by its correlation ID and follows each step in order: the customer's request, the tool call, where its details came from, the policy result, the risk score, any approval, the explanation and the outcome. Before relying on the records, the investigator confirms that the hash chain is intact.

### IRS-5.3 Explanations do not change decisions

A plain-English explanation of a decision is written after the decision is made and cites the policy sections that apply. An explanation can never change a decision. If an explanation cites a section that was not retrieved, it is discarded and a standard message is shown instead.

## 6. Recovery and review

### IRS-6.1 Releasing a quarantined agent

Only an administrator may release a quarantined agent, after reviewing why it was quarantined. The release is recorded with the administrator's identity and the reason.

### IRS-6.2 Unfreezing an account

A frozen account is unfrozen by staff, after the customer's identity has been verified and the reported transaction has been investigated. An AI agent cannot unfreeze an account.

### IRS-6.3 Review after an incident

Every critical incident is reviewed after it is closed. The review records the cause and any change to the bank's policy, which is then made as a new policy version under AAP-7.1.
