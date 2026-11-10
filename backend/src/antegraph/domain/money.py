"""Money helpers. Amounts are always integer minor units (USD cents)."""

MAX_AMOUNT_MINOR = 1_000_000_000_000  # $10,000,000,000.00


def format_usd(amount_minor: int) -> str:
    """Render integer cents as a dollar string, e.g. 1250000 -> "$12,500.00"."""
    if isinstance(amount_minor, bool) or not isinstance(amount_minor, int):
        raise TypeError("amount_minor must be an int")
    sign = "-" if amount_minor < 0 else ""
    dollars, cents = divmod(abs(amount_minor), 100)
    return f"{sign}${dollars:,}.{cents:02d}"
