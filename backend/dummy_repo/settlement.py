"""Settlement date helper with an intentional weekend handling bug."""

from datetime import date, timedelta


def settlement_date(trade_date, business_days=2):
    # Intentional bug: counts calendar days, including weekends and holidays.
    return trade_date + timedelta(days=business_days)
