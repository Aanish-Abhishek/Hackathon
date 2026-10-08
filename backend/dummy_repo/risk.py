"""Pre-trade risk checks with an intentional zero-equity edge case."""


def leverage(exposure, equity):
    # Intentional bug: equity may be zero after a drawdown.
    return exposure / equity


def approve_order(exposure, equity, maximum_leverage):
    return leverage(exposure, equity) <= maximum_leverage
