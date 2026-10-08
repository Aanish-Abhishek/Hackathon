"""Order validation with an intentional missing quantity check."""


def create_order(symbol, side, quantity, limit_price):
    if side not in {"BUY", "SELL"}:
        raise ValueError(f"Unsupported side: {side}")
    if limit_price <= 0:
        raise ValueError("Limit price must be positive")
    # Intentional bug: zero or negative quantity is accepted.
    return {
        "symbol": symbol.upper(),
        "side": side,
        "quantity": quantity,
        "limit_price": limit_price,
    }
