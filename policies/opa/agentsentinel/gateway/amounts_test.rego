package agentsentinel.gateway

test_amounts_are_read_as_whole_cents if {
	cents("0") == 0
	cents("0.01") == 1
	cents("0.5") == 50
	cents("0.05") == 5
	cents("120") == 12000
	cents("120.5") == 12050
	cents("120.00") == 12000
	cents("200.01") == 20001
	cents("5000.00") == 500000
	cents("-50.00") == -5000
	cents("-0.00") == 0
	cents("9999999999.99") == 999999999999
}

test_text_that_is_not_an_amount_has_no_value if {
	every text in ["", "-", ".5", "120.", "120.505", "1e3", "007.00", "01", "12,000.00", " 120.00", "120.00 ", "+120.00", "12345678901.00", "١٢٠"] {
		not cents(text)
	}
}

test_values_that_are_not_text_have_no_value if {
	every value in [120, 120.5, null, true, ["120.00"], {"amount": "120.00"}] {
		not cents(value)
	}
}

test_a_refund_within_the_automatic_limit_passes if {
	every amount in ["0.01", "1", "120.00", "199.99", "200", "200.00"] {
		answer := decision with input as refund_input(amount)
		count(answer.violations) == 0
	}
}

test_a_refund_above_the_automatic_limit_needs_a_person if {
	every amount in ["200.01", "750.00", "4999.99", "5000.00"] {
		answer := decision with input as refund_input(amount)
		answer.violations == {{
			"rule": "refund_above_automatic_limit",
			"decision": "HUMAN_REVIEW",
			"reason": "REFUND_OVER_LIMIT",
			"message": "Refunds above 200.00 USD need a person's approval.",
		}}
	}
}

test_a_refund_above_the_hard_cap_is_blocked_and_not_sent_for_review if {
	every amount in ["5000.01", "12000.00", "9999999999.99"] {
		answer := decision with input as refund_input(amount)
		answer.violations == {{
			"rule": "refund_above_hard_cap",
			"decision": "BLOCK",
			"reason": "REFUND_OVER_LIMIT",
			"message": "Refunds above 5000.00 USD are never allowed.",
		}}
	}
}

test_a_zero_or_negative_refund_is_blocked if {
	every amount in ["0", "0.00", "-0.00", "-0.01", "-50.00"] {
		answer := decision with input as refund_input(amount)
		answer.violations == {{
			"rule": "refund_amount_not_positive",
			"decision": "BLOCK",
			"reason": "INVALID_ARGUMENTS",
			"message": "The refund amount must be more than zero.",
		}}
	}
}

test_a_malformed_amount_is_blocked if {
	every amount in ["120.505", "1e3", "-", "", 120, 120.5, null, "007.00"] {
		answer := decision with input as refund_input(amount)
		rules(answer) == {"refund_amount_format"}
	}
}

test_a_refund_without_an_amount_is_blocked if {
	request := refund_input("120.00")
	without_amount := json.remove(request, ["action/arguments/amount"])
	rules(decision) == {"refund_amount_format"} with input as without_amount
}

test_amount_rules_only_apply_to_refunds if {
	answer := decision with input as action_input("close_dispute", "dispute", {"dispute_id": "DSP-000001", "amount": "-5"})
	count(answer.violations) == 0
}

test_the_limits_come_from_the_policy_data if {
	answer := decision with input as refund_input("150.00")
		with data.agentsentinel.settings.automatic_refund_limit as "100.00"
	rules(answer) == {"refund_above_automatic_limit"}
	some v in answer.violations
	v.message == "Refunds above 100.00 USD need a person's approval."
}
