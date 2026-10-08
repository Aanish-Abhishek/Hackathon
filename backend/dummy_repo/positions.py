"""Position updates with an intentional non-atomic read-modify-write."""


def apply_trade(position_store, account_id, symbol, quantity):
    current = position_store.get(account_id, symbol)
    updated = current + quantity
    # Intentional bug: concurrent trades can overwrite each other's updates.
    position_store.set(account_id, symbol, updated)
    return updated
