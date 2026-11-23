# Refund amounts: their format, their range and when a person must approve them.
# Rules R3 (invalid details) and R6 (refund above the automatic limit) in
# data/synthetic/labelling-rules.md. The limits are in data.agentsentinel.settings.
package agentsentinel.gateway

# R3: an amount is a string with at most two decimal places, such as "120.00", so it
# never passes through a floating point number on its way to the bank.
violations contains {
	"rule": "refund_amount_format",
	"decision": "BLOCK",
	"reason": "INVALID_ARGUMENTS",
	"message": "The refund amount must be written as a string such as \"120.00\", with at most two decimal places.",
} if {
	is_refund
	not valid_refund_amount
}

# R3: zero and negative refunds.
violations contains {
	"rule": "refund_amount_not_positive",
	"decision": "BLOCK",
	"reason": "INVALID_ARGUMENTS",
	"message": "The refund amount must be more than zero.",
} if {
	cents(refund_amount) <= 0
}

# R3: no refund above the hard cap, even with a person's approval.
violations contains {
	"rule": "refund_above_hard_cap",
	"decision": "BLOCK",
	"reason": "REFUND_OVER_LIMIT",
	"message": sprintf("Refunds above %s USD are never allowed.", [settings.refund_hard_cap]),
} if {
	cents(refund_amount) > cents(settings.refund_hard_cap)
}

# R6: above the automatic limit and up to the hard cap, a person decides (AT-04, AT-05).
violations contains {
	"rule": "refund_above_automatic_limit",
	"decision": "HUMAN_REVIEW",
	"reason": "REFUND_OVER_LIMIT",
	"message": sprintf("Refunds above %s USD need a person's approval.", [settings.automatic_refund_limit]),
} if {
	amount := cents(refund_amount)
	amount > cents(settings.automatic_refund_limit)
	amount <= cents(settings.refund_hard_cap)
}

is_refund if data.agentsentinel.refund_amount_argument[input.action.tool_name]

# A separate rule, so that a missing amount counts as invalid: `not cents(x)` would
# fail as a whole when x itself is undefined.
valid_refund_amount if cents(refund_amount)

refund_amount := input.action.arguments[data.agentsentinel.refund_amount_argument[input.action.tool_name]]

# A money amount in whole cents, or undefined when the text is not a valid amount.
# Leading zeros and exponents are refused, and so are more than ten digits before
# the decimal point.
cents(amount) := value if {
	is_string(amount)
	regex.match(`^-?(0|[1-9][0-9]{0,9})(\.[0-9]{1,2})?$`, amount)
	parts := split(trim_prefix(amount, "-"), ".")
	magnitude := (to_number(parts[0]) * 100) + hundredths(parts)
	value := signed(amount, magnitude)
}

hundredths(parts) := 0 if count(parts) == 1

# A "1" in front keeps to_number away from leading zeros such as "05".
hundredths(parts) := (to_number(concat("", ["1", parts[1]])) - 10) * 10 if {
	count(parts) == 2
	count(parts[1]) == 1
}

hundredths(parts) := to_number(concat("", ["1", parts[1]])) - 100 if {
	count(parts) == 2
	count(parts[1]) == 2
}

signed(amount, magnitude) := 0 - magnitude if startswith(amount, "-")

signed(amount, magnitude) := magnitude if not startswith(amount, "-")
