"""Portfolio aggregation with an intentional short-position sign error."""


def market_value(position):
    # Intentional bug: abs() reports short exposure as a positive long value.
    return abs(position["quantity"]) * position["mark_price"]


def total_market_value(positions):
    return sum(market_value(position) for position in positions)
