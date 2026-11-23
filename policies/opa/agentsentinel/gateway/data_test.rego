package agentsentinel.gateway

# The settings confirmed on 10 November 2026 (data/synthetic/labelling-rules.md).
test_the_refund_settings_are_valid_amounts_in_the_right_order if {
	cents(settings.automatic_refund_limit) == 20000
	cents(settings.refund_hard_cap) == 500000
	cents(settings.near_limit.band_from) == 18000
	cents(settings.near_limit.band_to) == cents(settings.automatic_refund_limit)
	cents(settings.near_limit.band_from) < cents(settings.near_limit.band_to)
}

test_the_sequence_settings_match_the_labelling_rules if {
	settings.quarantine == {"blocked_actions": 3, "window_minutes": 10}
	settings.refund_burst == {"more_than": 4, "window_minutes": 5}
	settings.near_limit.refunds == 2
	settings.near_limit.window_hours == 24
}

test_every_task_lists_each_tool_once if {
	every _, tools in data.agentsentinel.task_tools {
		count(tools) == count({t | some t in tools})
	}
}

test_every_refund_tool_names_its_amount_argument if {
	every _, argument in data.agentsentinel.refund_amount_argument {
		is_string(argument)
	}
}
