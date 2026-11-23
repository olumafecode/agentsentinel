package agentsentinel.gateway

# The task-to-tool table the Product Owner confirmed on 23 November 2026.
allowed_for_vera := {
	["account_inquiry", "get_customer"],
	["account_inquiry", "get_accounts"],
	["account_inquiry", "get_transactions"],
	["refund_request", "get_customer"],
	["refund_request", "get_accounts"],
	["refund_request", "get_transactions"],
	["refund_request", "issue_refund"],
	["profile_update", "get_customer"],
	["profile_update", "update_address"],
	["dispute", "get_customer"],
	["dispute", "get_accounts"],
	["dispute", "get_transactions"],
	["dispute", "close_dispute"],
	["dispute", "freeze_account"],
}

test_vera_may_use_each_tool_for_the_tasks_that_allow_it if {
	every pair in allowed_for_vera {
		answer := decision with input as action_input(pair[1], pair[0], arguments_for(pair[1]))
		count(answer.violations) == 0
	}
}

test_every_other_task_and_tool_pair_is_blocked if {
	tasks := {"account_inquiry", "refund_request", "profile_update", "dispute"}
	every task in tasks {
		every tool in vera.allowed_tools {
			allowed := [task, tool] in allowed_for_vera
			blocked := "tool_not_allowed_for_task" in rules(decision) with input as action_input(tool, task, arguments_for(tool))
			allowed != blocked
		}
	}
}

test_a_refund_is_only_issued_in_a_refund_request if {
	answer := decision with input as action_input("issue_refund", "dispute", arguments_for("issue_refund"))
	answer.violations == {{
		"rule": "tool_not_allowed_for_task",
		"decision": "BLOCK",
		"reason": "TOOL_NOT_ALLOWED",
		"message": "issue_refund is not allowed for dispute tasks.",
	}}
}

test_an_account_can_be_frozen_while_handling_a_suspected_fraud if {
	answer := decision with input as action_input("freeze_account", "dispute", {"account_id": "ACC-00000123", "reason": "Suspected fraud"})
	count(answer.violations) == 0
}

test_an_account_cannot_be_frozen_during_an_account_inquiry if {
	"tool_not_allowed_for_task" in rules(decision) with input as action_input("freeze_account", "account_inquiry", {})
}

test_a_tool_outside_the_agents_allowlist_is_blocked if {
	limited := object.union(vera, {"allowed_tools": ["get_customer"]})
	answer := decision with input as object.union(action_input("get_transactions", "account_inquiry", {}), {"agent": limited})
	answer.violations == {{
		"rule": "tool_not_allowed_for_agent",
		"decision": "BLOCK",
		"reason": "TOOL_NOT_ALLOWED",
		"message": "Vera is not allowed to use get_transactions.",
	}}
}

test_staff_tools_are_not_in_veras_allowlist if {
	every tool in ["export_customers", "reset_credentials"] {
		"tool_not_allowed_for_agent" in rules(decision) with input as action_input(tool, "admin_maintenance", {})
	}
}

test_bulk_export_is_denied_for_every_task if {
	every task in ["account_inquiry", "refund_request", "profile_update", "dispute", "admin_maintenance"] {
		"bulk_export" in rules(decision) with input as action_input("export_customers", task, {})
	}
}

test_bulk_export_is_denied_even_for_an_agent_allowed_the_tool if {
	staff := object.union(vera, {"allowed_tools": ["export_customers"]})
	answer := decision with input as object.union(action_input("export_customers", "admin_maintenance", {}), {"agent": staff})
	answer.violations == {{
		"rule": "bulk_export",
		"decision": "BLOCK",
		"reason": "POLICY_DENY",
		"message": "Exporting customer records in bulk is never allowed through an agent.",
	}}
}

test_vera_asking_for_an_export_breaks_three_rules if {
	rules(decision) == {"bulk_export", "tool_not_allowed_for_agent", "tool_not_allowed_for_task"} with input as action_input("export_customers", "account_inquiry", {})
}

test_an_unknown_task_allows_no_tools if {
	"tool_not_allowed_for_task" in rules(decision) with input as action_input("get_customer", "something_else", {})
}

test_an_agent_without_a_name_is_still_named_in_the_message if {
	nameless := json.remove(action_input("export_customers", "admin_maintenance", {}), ["agent/name"])
	answer := decision with input as nameless
	some v in answer.violations
	v.message == "This agent is not allowed to use export_customers."
}
