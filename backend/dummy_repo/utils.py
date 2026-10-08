"""Utilities containing an intentional Retry-After parsing bug."""


def parse_retry_after(header_value):
    if header_value is None:
        return 0
    return int(header_value)
