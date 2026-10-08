"""Market data cache with an intentional missing expiration check."""


def get_quote(cache, provider, symbol):
    quote = cache.get(symbol)
    if quote is not None:
        # Intentional bug: stale cached quotes are returned indefinitely.
        return quote
    quote = provider.fetch_quote(symbol)
    cache.set(symbol, quote)
    return quote
