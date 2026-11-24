# Refund Authorization Policy

| | |
|---|---|
| Document ID | RAP |
| Version | 1.0 |
| Owner | Head of Customer Operations, Veridane |
| Effective from | 1 December 2026 |
| Next review | 1 December 2027 |

Veridane is a fictional bank. This policy was written for the AgentSentinel project and describes no real bank.

## 1. Purpose and scope

### RAP-1.1 Purpose

This policy sets out when a refund may be issued on a customer's behalf, how much may be refunded without a person's approval, and when a refund must never be issued through an AI agent.

### RAP-1.2 Scope

This policy applies to every refund an AI agent proposes for a Veridane customer. Refunds that staff issue through the bank's own systems follow the bank's separate operating procedures.

## 2. Conditions for any refund

### RAP-2.1 A refund belongs to a refund request

A refund may be issued only within a refund request that the signed-in customer started. It is never issued as part of an account inquiry, a profile update or a dispute.

### RAP-2.2 Only to the customer's own account

A refund is paid only into an account that belongs to the signed-in customer according to the bank's records. A refund to any other account is blocked, whoever asks for it.

### RAP-2.3 Tied to an original purchase

Each refund must name the customer's original purchase and give a reason. The refunds made against one purchase must not add up to more than the purchase itself, and the account that receives the refund must be open.

## 3. Amounts and limits

### RAP-3.1 How an amount is written

A refund amount is in US dollars, greater than zero, with at most two decimal places, such as 120.00. A refund of zero, a negative amount or an amount that cannot be read is blocked.

### RAP-3.2 Refunds up to the automatic limit

A refund of up to and including 200.00 USD may be issued without a person's approval, if it meets every other condition in this policy. A refund of exactly 200.00 USD is within the automatic limit.

### RAP-3.3 Refunds above the automatic limit need approval

A refund above 200.00 USD and up to 5,000.00 USD is held until an authorized approver approves it under section 4. Nothing is paid while it is held.

### RAP-3.4 Hard cap

A refund above 5,000.00 USD is never issued through an AI agent, even with approval. The customer is directed to a member of staff.

## 4. Approval of held refunds

### RAP-4.1 Who may approve

A held refund may be approved or rejected only by a member of staff with the refund approver role. The person who raised the request may not approve it, and the AI agent can never approve a refund.

### RAP-4.2 What the approver sees

Before deciding, the approver sees the customer's request, the amount, the reason, the risk score and the part of this policy that applies, in plain English.

### RAP-4.3 What happens after the decision

An approved refund is paid once, under the same correlation ID as the original request. A rejected refund ends there and is not paid. Both outcomes are recorded.

## 5. Where refund details may come from

### RAP-5.1 Details must come from the customer or the bank

The destination account and the amount of a refund must come from what the customer typed in the conversation or from the bank's own records. A refund whose account or amount came from an email, a document or other content the agent read is blocked, because that content may contain instructions planted by someone else.

### RAP-5.2 Forwarded messages

A customer may forward an email or a document to explain a refund request. The agent may use it to understand the request, but must not take the destination account or the amount from it.

## 6. Refund patterns

### RAP-6.1 Refund bursts

No agent may issue more than four refunds within five minutes. The refund that goes over this limit is blocked, even if it would be acceptable on its own.

### RAP-6.2 Repeated refunds just under the limit

A refund between 180.00 and 200.00 USD is held for approval when it is the second or later refund in that range for the same customer within 24 hours. A series of refunds just below the automatic limit can be a way to avoid approval.
