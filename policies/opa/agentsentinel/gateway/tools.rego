# Which tools an agent may use, and for which task.
# Rules R1 (bulk scope) and R2 (wrong tool) in data/synthetic/labelling-rules.md.
package agentsentinel.gateway

# R1: customer records are never exported in bulk through an agent, whatever the task.
violations contains {
	"rule": "bulk_export",
	"decision": "BLOCK",
	"reason": "POLICY_DENY",
	"message": "Exporting customer records in bulk is never allowed through an agent.",
} if {
	input.action.tool_name in data.agentsentinel.bulk_export_tools
}

# R2: the agent's own allowlist, from the gateway's agent registry.
violations contains {
	"rule": "tool_not_allowed_for_agent",
	"decision": "BLOCK",
	"reason": "TOOL_NOT_ALLOWED",
	"message": sprintf("%s is not allowed to use %s.", [agent_name, input.action.tool_name]),
} if {
	is_string(input.action.tool_name)
	not input.action.tool_name in object.get(input.agent, "allowed_tools", [])
}

# R2: the tools each task allows, as confirmed by the Product Owner.
violations contains {
	"rule": "tool_not_allowed_for_task",
	"decision": "BLOCK",
	"reason": "TOOL_NOT_ALLOWED",
	"message": sprintf("%s is not allowed for %s tasks.", [input.action.tool_name, input.action.task_type]),
} if {
	is_string(input.action.tool_name)
	is_string(input.action.task_type)
	not input.action.tool_name in object.get(data.agentsentinel.task_tools, input.action.task_type, [])
}

agent_name := object.get(input.agent, "name", "This agent")
