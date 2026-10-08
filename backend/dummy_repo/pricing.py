"""Trade fee calculation with an intentional binary-float rounding issue."""


def calculate_fee(notional, rate):
    # Intentional bug: float arithmetic can produce incorrect currency cents.
    return round(notional * rate, 2)
