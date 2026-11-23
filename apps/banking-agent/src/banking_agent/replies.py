"""What Vera tells the customer after each proposal.

In scripted mode the wording is fixed so that transcripts are repeatable. In live
mode (US-24) the language model writes the replies, but a refusal must still say the
action was refused.
"""

from typing import Any

from sentinel_contracts import ActionOutcome, Decision, ExecutionStatus

ALREADY_REFUSED = "I already tried that and it was refused, so I won't try it again."
ALREADY_HELD = "That request is already waiting for approval."
UNAVAILABLE = (
    "I can't reach the bank's systems right now, so nothing was done. "
    "Please try again in a moment."
)
DISCONNECTED = "Something is wrong with my connection to the bank's systems, so I have to stop here."
NOTHING_TO_DO = "How else can I help?"


def describe(tool_name: str, outcome: ActionOutcome) -> str:
    """One sentence about what happened to a proposed action."""
    decision = outcome.decision
    if decision.decision is Decision.BLOCK:
        return f"I'm sorry, I can't do that. {decision.summary}"
    if decision.decision is Decision.QUARANTINE:
        return f"I'm sorry, I can't continue. {decision.summary}"
    if decision.decision is Decision.HUMAN_REVIEW:
        return (
            "That needs approval from a member of staff "
            f"(request {decision.approval_id}). I'll let you know once it has been reviewed."
        )
    execution = outcome.execution
    if execution is None or execution.status is ExecutionStatus.FAILED:
        return (
            "I couldn't confirm with the bank whether that went through, "
            "so please don't repeat it until it has been checked."
        )
    if execution.status is ExecutionStatus.REJECTED:
        message = execution.error.message if execution.error else "no reason given"
        return f"The bank couldn't complete that: {message.rstrip('.')}."
    return _success(tool_name, execution.result)


def _success(tool_name: str, result: Any) -> str:
    data = result if isinstance(result, dict) else {}
    match tool_name:
        case "get_transactions" if isinstance(result, list):
            plural = "" if len(result) == 1 else "s"
            return f"Here are your {len(result)} most recent transaction{plural}."
        case "get_accounts" if isinstance(result, list):
            plural = "" if len(result) == 1 else "s"
            return f"You have {len(result)} account{plural} with us."
        case "get_customer" if "full_name" in data:
            return f"I have your profile, {data['full_name']}."
        case "update_address" if "address" in data:
            return f"Your mailing address is now {data['address']}."
        case "issue_refund" if {"amount", "account_id"} <= data.keys():
            return f"Your refund of {data['amount']} USD has been issued to {data['account_id']}."
        case "close_dispute" if "dispute_id" in data:
            return f"Dispute {data['dispute_id']} is now closed."
        case "freeze_account" if "account_id" in data:
            return (
                f"Account {data['account_id']} is now frozen, "
                "so no more payments can leave it."
            )
    return "Done."
