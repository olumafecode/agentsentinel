# Customer Data Access Policy

| | |
|---|---|
| Document ID | CDA |
| Version | 1.0 |
| Owner | Data Protection Officer, Veridane |
| Effective from | 1 December 2026 |
| Next review | 1 December 2027 |

Veridane is a fictional bank. This policy was written for the AgentSentinel project and describes no real bank.

## 1. Purpose and scope

### CDA-1.1 Purpose

This policy protects customers' personal and financial information when an AI agent reads or changes it for them. It limits each conversation to the data of the customer who is signed in, and to what their request needs.

### CDA-1.2 Scope

This policy applies to every read or change of customer data that an AI agent makes through Veridane's banking tools: profiles, mailing addresses, accounts, balances, transactions and disputes.

## 2. Whose data an agent may use

### CDA-2.1 Only the signed-in customer

During a conversation, an agent may read or change only the data of the customer who signed in to start it. An action that names any other customer is blocked.

### CDA-2.2 Records must belong to the customer

Every account, transaction or dispute that an action names must belong to the signed-in customer according to the bank's own records. This is checked against those records before the action runs, whatever the agent or the customer says about who owns it. An action that names a record belonging to someone else is blocked.

### CDA-2.3 No access for relatives, friends or third parties

A customer cannot ask an agent for another person's information, even a relative's, a neighbor's or that of someone who says they have permission. Such a request is refused.

### CDA-2.4 No bulk access

An agent may never export or list the records of many customers at once. Bulk exports are reserved for staff under separate controls and are always blocked when an agent asks for them.

## 3. Using no more data than needed

### CDA-3.1 Only what the request needs

An agent reads only the data the customer's request needs. For example, a question about recent payments needs recent transactions, not the customer's full history or profile.

### CDA-3.2 Limited transaction history

A single request may return at most the 100 most recent transactions. A customer who needs a longer history is directed to their statements.

## 4. Changing customer data

### CDA-4.1 Change only what the customer asked

An agent may change a customer's mailing address only within a profile update, and only to the address the customer gave. It must not change any other detail as part of the same request.

### CDA-4.2 Sign-in and recovery details are not changed by agents

An agent may never reset or change a customer's password, sign-in credentials or recovery email. Those changes are made by staff after the customer's identity has been verified.

## 5. Records and accountability

### CDA-5.1 Every access is recorded

Each read or change of customer data is recorded with the agent, the session, the customer, the decision and a correlation ID, so that any access can be traced later.

### CDA-5.2 Records cannot be altered

Access records are append-only and linked by hashes, so that a record changed or removed after it was written can be detected. No one, including administrators, may edit or delete them.

### CDA-5.3 No secrets in records or logs

Records and logs must not contain passwords, keys or authorization tokens. They identify agents and sessions by ID, and store keys only in a form that cannot be read back.
