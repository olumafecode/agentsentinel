# METADATA
# title: Bank policy for actions proposed by AI agents
# description: |
#   The Sentinel Gateway asks for data.agentsentinel.gateway.decision on every action
#   that passes its context checks (US-02a, ADR-015). The answer lists every rule the
#   action breaks. An empty list means the policy has no objection; it never allows an
#   action on its own, because the gateway's other checks still run.
#
#   Input:
#     agent   agent_id, name and allowed_tools, from the gateway's agent registry
#     tool    tool_name, category, high_impact and sensitive_parameters
#     action  task_type, tool_name, customer_scope, arguments and provenance_labels
#
#   Each violation has a rule name, the decision it asks for (BLOCK or HUMAN_REVIEW),
#   a reason code from sentinel_contracts.ReasonCode and a one-sentence message.
package agentsentinel.gateway

settings := data.agentsentinel.settings

decision := {"violations": violations}

# Deny by default: without the whole action there is nothing reliable to judge.
violations contains {
	"rule": "incomplete_input",
	"decision": "BLOCK",
	"reason": "MISSING_CONTEXT",
	"message": "The policy was not given the whole action, so it is blocked.",
} if {
	not complete_input
}

complete_input if {
	is_string(input.action.tool_name)
	is_string(input.action.task_type)
	is_object(input.action.arguments)
	is_array(input.agent.allowed_tools)
}
