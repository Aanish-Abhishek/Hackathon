"""Trade reconciliation with an intentional floating-point comparison."""


def trades_match(internal_amount, clearing_amount):
    # Intentional bug: exact float comparison can reject equivalent amounts.
    return internal_amount == clearing_amount
