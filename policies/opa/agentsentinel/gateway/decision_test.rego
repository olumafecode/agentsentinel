package agentsentinel.gateway

test_an_allowed_action_has_no_violations if {
	decision == {"violations": set()} with input as action_input("get_transactions", "account_inquiry", {"customer_id": "CUS-000123", "limit": 5})
}

test_an_action_that_breaks_several_rules_lists_them_all if {
	answer := decision with input as action_input("issue_refund", "account_inquiry", {"amount": "-5.00"})
	rules(answer) == {"tool_not_allowed_for_task", "refund_amount_not_positive"}
}

test_an_incomplete_input_is_blocked if {
	complete := action_input("get_customer", "account_inquiry", {})
	every broken in [
		{},
		json.remove(complete, ["agent"]),
		json.remove(complete, ["agent/allowed_tools"]),
		json.remove(complete, ["action/tool_name"]),
		json.remove(complete, ["action/task_type"]),
		json.remove(complete, ["action/arguments"]),
		json.patch(complete, [{"op": "replace", "path": "/action/arguments", "value": []}]),
		json.patch(complete, [{"op": "replace", "path": "/action/tool_name", "value": 7}]),
	] {
		some v in decision.violations with input as broken
		v == {
			"rule": "incomplete_input",
			"decision": "BLOCK",
			"reason": "MISSING_CONTEXT",
			"message": "The policy was not given the whole action, so it is blocked.",
		}
	}
}

test_every_violation_has_the_fields_the_gateway_reads if {
	inputs := [
		action_input("export_customers", "account_inquiry", {}),
		refund_input("-1"),
		refund_input("1e3"),
		refund_input("6000.00"),
		refund_input("300.00"),
		{},
	]
	every request in inputs {
		answer := decision with input as request
		every v in answer.violations {
			object.keys(v) == {"rule", "decision", "reason", "message"}
			regex.match(`^[a-z][a-z0-9_]{2,60}$`, v.rule)
			v.decision in {"BLOCK", "HUMAN_REVIEW"}
			regex.match(`^[A-Z][A-Z_]+$`, v.reason)
			count(v.message) >= 3
			count(v.message) <= 300
		}
	}
}
