from datetime import UTC, datetime
from itertools import count
from typing import Any

from sqlalchemy.orm import Session

from app.models import Order, OrderItem, Product, Setting, Variant
from app.services.orders import OrderLine, calculate_totals
from app.services.shipping import COURIER_KEY, FREE_THRESHOLD_KEY, LOCKER_KEY

_sequence = count(1)


def make_product(db: Session, **overrides: Any) -> Product:
    n = next(_sequence)
    product = Product(
        **{
            "slug": f"swieczka-{n}",
            "name": f"Świeczka {n}",
            "category": "swieczki",
            "price_grosze": 4900,
            "weight_g": 180,
            **overrides,
        }
    )
    db.add(product)
    db.flush()
    return product


def make_variant(db: Session, product: Product | None = None, **overrides: Any) -> Variant:
    variant = Variant(
        **{
            "product": product or make_product(db),
            "name": f"kolor {next(_sequence)}",
            "hex": "#FFFFFF",
            "stock": 5,
            **overrides,
        }
    )
    db.add(variant)
    db.flush()
    return variant


def make_order(
    db: Session,
    items: list[tuple[Variant, int]] | None = None,
    shipping_grosze: int = 1299,
    **overrides: Any,
) -> Order:
    """Order with item copies and totals computed from the variants' current prices."""
    if items is None:
        items = [(make_variant(db), 1)]

    totals = calculate_totals(
        [OrderLine(variant.product.price_grosze, qty) for variant, qty in items],
        shipping_grosze,
    )
    order = Order(
        **{
            "email": "klient@example.com",
            "phone": "+48500600700",
            "full_name": "Anna Kowalska",
            "terms_accepted_at": datetime.now(UTC),
            "shipping_method": "locker",
            "locker_id": "WAW01M",
            "subtotal_grosze": totals.subtotal_grosze,
            "shipping_grosze": totals.shipping_grosze,
            "total_grosze": totals.total_grosze,
            **overrides,
        }
    )
    order.items = [
        OrderItem(
            variant_id=variant.id,
            product_name=variant.product.name,
            variant_name=variant.name,
            unit_price_grosze=variant.product.price_grosze,
            qty=qty,
        )
        for variant, qty in items
    ]
    db.add(order)
    db.flush()
    return order


def add_shipping_settings(
    db: Session, locker: int = 1400, courier: int = 1800, free_from: int = 20000
) -> None:
    for key, value in {
        LOCKER_KEY: locker,
        COURIER_KEY: courier,
        FREE_THRESHOLD_KEY: free_from,
    }.items():
        db.add(Setting(key=key, value=str(value)))
    db.flush()
