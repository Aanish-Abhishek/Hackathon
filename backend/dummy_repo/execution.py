"""Execution handling with an intentional overfill acceptance bug."""


def apply_fill(order, fill_quantity, fill_price):
    # Intentional bug: fills larger than the remaining order are accepted.
    order["filled_quantity"] += fill_quantity
    order["average_price"] = fill_price
    if order["filled_quantity"] >= order["quantity"]:
        order["status"] = "FILLED"
    return order
