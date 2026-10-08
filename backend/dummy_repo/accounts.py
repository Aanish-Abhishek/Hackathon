"""Account access check with an intentional fail-open authorization bug."""


def can_trade(account, user_id):
    if account is None:
        # Intentional bug: missing account data grants access.
        return True
    return user_id in account.get("authorized_traders", [])
