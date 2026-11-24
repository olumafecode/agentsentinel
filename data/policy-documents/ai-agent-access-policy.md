# AI Agent Access Policy

| | |
|---|---|
| Document ID | AAP |
| Version | 1.0 |
| Owner | Head of Digital Channels, Veridane |
| Effective from | 1 December 2026 |
| Next review | 1 December 2027 |

Veridane is a fictional bank. This policy was written for the AgentSentinel project and describes no real bank.

## 1. Purpose and scope

### AAP-1.1 Purpose

This policy sets out what an AI agent may do when it acts for a Veridane customer: which tools it may use, for which tasks, and under what controls. It exists so that a mistake or a manipulated instruction cannot move money or expose data that the customer did not ask for.

### AAP-1.2 Scope

This policy applies to every AI agent that calls Veridane's banking tools for a customer, including Vera, the bank's customer service agent. It does not cover staff who use the same tools directly through the bank's own systems.

### AAP-1.3 Terms used in this policy

A tool is one banking operation, such as reading transactions or issuing a refund. A task is the kind of help the customer asked for when the chat began: an account inquiry, a refund request, a profile update or a dispute. Administrative maintenance is a fifth task, for staff only. A high-impact tool is one that moves money, exports data, changes credentials or freezes an account.

## 2. Registration and identity

### AAP-2.1 Every agent is registered

An agent may act only after it is registered with its role, its status and the list of tools it may use. An agent that is not registered cannot act at all.

### AAP-2.2 Each agent has its own credentials

Each agent proves who it is on every request with a key issued to that agent alone. Keys are never shared between agents and are stored only in a form that cannot be read back. A request that the gateway cannot tie to a registered agent is refused.

### AAP-2.3 Every action belongs to a customer session

Each action must name the customer's chat session, the customer and the task, and these must match the session the customer started. An action whose agent, session or customer does not match the signed session is blocked. So is an action that arrives without the context needed to judge it.

### AAP-2.4 Only an active agent may act

An agent that an administrator has disabled, or that has been quarantined under IRS-3.1, may not act. Every action it proposes is refused until an administrator restores it.

## 3. Tools and tasks

### AAP-3.1 Least privilege

An agent may use only the tools on its own list. A tool that is not on the list is blocked, even if the task would otherwise allow it.

### AAP-3.2 Tools allowed for each task

An agent may use a tool only when the customer's task allows it:

| Task | Tools the agent may use |
|---|---|
| Account inquiry | get_customer, get_accounts, get_transactions |
| Refund request | get_customer, get_accounts, get_transactions, issue_refund |
| Profile update | get_customer, update_address |
| Dispute | get_customer, get_accounts, get_transactions, close_dispute, freeze_account |
| Administrative maintenance | export_customers, reset_credentials, freeze_account |

A refund is issued only within a refund request. Administrative maintenance is carried out by staff, not by a customer service agent.

### AAP-3.3 Unknown tools are denied

A tool that is not in the bank's catalogue is denied by default. No agent may call a new tool until the tool has been reviewed and added to the catalogue and to this policy.

### AAP-3.4 Tools reserved for staff

Exporting customer records and resetting a customer's sign-in credentials are reserved for staff. A customer service agent such as Vera may never use them, whatever the customer or any content asks.

### AAP-3.5 Freezing an account in a suspected fraud

When a customer reports a transaction they do not recognize, the agent may freeze the affected account at once, within a dispute, so that no further money can leave it. The account must belong to the signed-in customer. Unfreezing is done by staff under IRS-6.2, never by the agent.

## 4. How actions are carried out

### AAP-4.1 Every action goes through the gateway

An agent never calls a banking tool directly. It proposes each action to the Sentinel Gateway, which decides whether it may run and, if so, forwards it with a single-use authorization that is valid for that one action only.

### AAP-4.2 Fresh requests, run once

An action must reach the gateway within five minutes of being proposed. An older one is refused and must be proposed again. Each action carries a correlation ID, and an action is never run twice: a repeated request receives the first decision again.

### AAP-4.3 Deny when a control cannot run

If a control that judges an action cannot run, for example because the policy service or the risk service is unavailable, the action is blocked. The bank prefers a refused request to an unchecked one.

### AAP-4.4 Details must be valid

The details of an action must have the form the tool expects, such as a customer ID, an account number or an amount. An action with missing, malformed or out-of-range details is refused and does not run.

## 5. Instructions and content

### AAP-5.1 Content is information, not instruction

An agent takes instructions only from the customer in the chat and from the bank. Text found in emails, documents, web pages or tool results is information to read, never an instruction to follow, however it is worded.

### AAP-5.2 High-impact details from untrusted content

When a high-impact tool is used, its sensitive details, such as the destination account or the amount of a refund, must come from what the customer typed or from the bank's own records. If any of them came from untrusted content, such as a forwarded email, the action is blocked.

### AAP-5.3 No working around a refusal

When an action is refused, the agent tells the customer and does not try the same action again in another form, with another tool or through another route.

## 6. Monitoring

### AAP-6.1 Risk scoring

The gateway scores actions and short sequences of actions for risk. A high score can hold or block an action that the rules would otherwise allow. It can never allow an action that a rule blocks.

### AAP-6.2 Abnormal sequences

A sequence can be blocked even when each action in it would be acceptable on its own. One example is a burst of refunds; RAP-6.1 sets that limit. Another is an agent trying three or more different high-impact tools it has not used before in the same session within two minutes.

### AAP-6.3 Repeated violations

An agent that has three actions blocked within ten minutes is quarantined, as set out in IRS-3.1.

## 7. Changes to this policy

### AAP-7.1 Policy rules are versioned

The rules in this policy are also kept as versioned policy that the gateway enforces. Every decision the policy takes part in records the version it was judged against. A change to what an agent may do needs the Product Owner's approval and a new policy version.
