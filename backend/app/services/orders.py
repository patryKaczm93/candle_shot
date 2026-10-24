from collections.abc import Sequence
from dataclasses import dataclass

from app.models import MAX_QTY_PER_ITEM


@dataclass(frozen=True)
class OrderLine:
    unit_price_grosze: int
    qty: int


@dataclass(frozen=True)
class OrderTotals:
    subtotal_grosze: int
    shipping_grosze: int
    total_grosze: int


def _require_int(value: object, name: str) -> int:
    # bool is a subclass of int; floats must never reach money code.
    if type(value) is not int:
        raise TypeError(f"{name} must be int, got {type(value).__name__}")
    return value


def calculate_totals(lines: Sequence[OrderLine], shipping_grosze: int) -> OrderTotals:
    """Order totals in grosze. Prices must already come from the database, never the request."""
    if not lines:
        raise ValueError("order must have at least one line")

    subtotal = 0
    for line in lines:
        price = _require_int(line.unit_price_grosze, "unit_price_grosze")
        qty = _require_int(line.qty, "qty")
        if price <= 0:
            raise ValueError("unit_price_grosze must be positive")
        if not 1 <= qty <= MAX_QTY_PER_ITEM:
            raise ValueError(f"qty must be between 1 and {MAX_QTY_PER_ITEM}")
        subtotal += price * qty

    shipping = _require_int(shipping_grosze, "shipping_grosze")
    if shipping < 0:
        raise ValueError("shipping_grosze must not be negative")

    return OrderTotals(
        subtotal_grosze=subtotal,
        shipping_grosze=shipping,
        total_grosze=subtotal + shipping,
    )
