# Inputs shared by the policy tests: Vera, as the gateway's agent registry lists her.
package agentsentinel.gateway

vera := {
	"agent_id": "AGT-001",
	"name": "Vera",
	"allowed_tools": [
		"get_customer",
		"get_accounts",
		"get_transactions",
		"update_address",
		"issue_refund",
		"close_dispute",
		"freeze_account",
	],
}

action_input(tool_name, task_type, arguments) := {
	"agent": vera,
	"tool": {"tool_name": tool_name},
	"action": {
		"task_type": task_type,
		"tool_name": tool_name,
		"customer_scope": "CUS-000123",
		"arguments": arguments,
		"provenance_labels": {},
	},
}

refund_arguments(amount) := {
	"account_id": "ACC-00000123",
	"amount": amount,
	"original_transaction_id": "TXN-0000004568",
	"reason": "Duplicate charge",
}

refund_input(amount) := action_input("issue_refund", "refund_request", refund_arguments(amount))

# Arguments that pass the amount rules, so a test about tools is only about tools.
arguments_for(tool_name) := refund_arguments("120.00") if tool_name == "issue_refund"

arguments_for(tool_name) := {} if tool_name != "issue_refund"

rules(answer) := {v.rule | some v in answer.violations}
