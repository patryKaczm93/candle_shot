import re
from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import OrderItem, Product, StripeEvent
from app.services.orders import OrderLine, calculate_totals
from tests.factories import make_order, make_product, make_variant

# --- Order totals (pure function) ---


def test_order_totals_with_items_and_shipping_sum_in_grosze() -> None:
    totals = calculate_totals(
        [OrderLine(unit_price_grosze=4900, qty=2), OrderLine(unit_price_grosze=6450, qty=1)],
        shipping_grosze=1299,
    )

    assert totals.subtotal_grosze == 16250
    assert totals.shipping_grosze == 1299
    assert totals.total_grosze == 17549
    assert all(
        type(v) is int
        for v in (totals.subtotal_grosze, totals.shipping_grosze, totals.total_grosze)
    )


@pytest.mark.parametrize(
    ("price", "qty", "shipping"),
    [
        (49.0, 1, 0),  # float price
        (True, 1, 0),  # bool price
        (4900, 1.0, 0),  # float qty
        (4900, True, 0),  # bool qty
        (4900, 1, 12.99),  # float shipping
    ],
)
def test_order_totals_with_non_int_value_raises_type_error(
    price: object, qty: object, shipping: object
) -> None:
    with pytest.raises(TypeError):
        calculate_totals([OrderLine(price, qty)], shipping)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("price", "qty", "shipping"),
    [
        (4900, 0, 0),
        (4900, 11, 0),
        (4900, -1, 0),
        (0, 1, 0),
        (-100, 1, 0),
        (4900, 1, -1),
    ],
)
def test_order_totals_with_value_out_of_range_raises_value_error(
    price: int, qty: int, shipping: int
) -> None:
    with pytest.raises(ValueError):
        calculate_totals([OrderLine(price, qty)], shipping)


def test_order_totals_without_lines_raises_value_error() -> None:
    with pytest.raises(ValueError):
        calculate_totals([], shipping_grosze=1299)


# --- Saved order ---


def test_saved_order_with_two_items_stores_totals_and_item_copies(db: Session) -> None:
    candle = make_variant(db, product=make_product(db, name="Wanilia", price_grosze=4900))
    figa = make_variant(db, product=make_product(db, name="Figa", price_grosze=6450))

    order = make_order(db, items=[(candle, 2), (figa, 1)], shipping_grosze=1299)
    db.refresh(order)

    assert (order.subtotal_grosze, order.shipping_grosze, order.total_grosze) == (
        16250,
        1299,
        17549,
    )
    assert order.status == "pending"
    assert sorted((i.product_name, i.unit_price_grosze, i.qty) for i in order.items) == [
        ("Figa", 6450, 1),
        ("Wanilia", 4900, 2),
    ]


def test_order_item_keeps_price_after_product_price_change(db: Session) -> None:
    # Documents the model: items hold copies. Ignoring request prices is tested in 5.1.
    product = make_product(db, price_grosze=4900)
    order = make_order(db, items=[(make_variant(db, product=product), 1)])

    product.price_grosze = 9900
    db.flush()
    db.refresh(order)

    assert order.items[0].unit_price_grosze == 4900
    assert order.total_grosze == 4900 + 1299


def test_order_number_is_random_code_without_ambiguous_characters(db: Session) -> None:
    first = make_order(db)
    second = make_order(db)

    for order in (first, second):
        assert re.fullmatch(r"PM-[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{6}", order.number)
    assert first.number != second.number


# --- Database constraints: the last line of defence for money and stock ---


def assert_rejected(
    db: Session, constraint: str | set[str], action: Callable[[], object] | None = None
) -> None:
    """The write fails on exactly this constraint, not on some unrelated one."""
    with pytest.raises(IntegrityError) as exc:
        (action or db.flush)()
    db.rollback()
    expected = {constraint} if isinstance(constraint, str) else constraint
    assert exc.value.orig.diag.constraint_name in expected  # type: ignore[union-attr]


def test_order_with_total_not_equal_to_sum_is_rejected(db: Session) -> None:
    order = make_order(db)
    order.total_grosze -= 1
    assert_rejected(db, "ck_orders_total_is_sum")


def test_order_with_negative_shipping_is_rejected(db: Session) -> None:
    # Total still equals the sum, so only the non-negative check can catch it.
    order = make_order(db, shipping_grosze=0)
    order.subtotal_grosze += 100
    order.shipping_grosze = -100
    assert_rejected(db, "ck_orders_amounts_non_negative")


def test_variant_with_negative_stock_is_rejected(db: Session) -> None:
    variant = make_variant(db, stock=1)
    variant.stock = -1
    assert_rejected(db, "ck_variants_stock_non_negative")


@pytest.mark.parametrize("qty", [0, 11])
def test_order_item_with_qty_out_of_range_is_rejected(db: Session, qty: int) -> None:
    order = make_order(db)
    order.items[0].qty = qty
    assert_rejected(db, "ck_order_items_qty_in_range")


def test_order_item_with_zero_price_is_rejected(db: Session) -> None:
    order = make_order(db)
    order.items[0].unit_price_grosze = 0
    assert_rejected(db, "ck_order_items_unit_price_positive")


def test_product_with_zero_price_is_rejected(db: Session) -> None:
    product = make_product(db)
    product.price_grosze = 0
    assert_rejected(db, "ck_products_price_positive")


def test_order_with_unknown_status_is_rejected(db: Session) -> None:
    order = make_order(db)
    order.status = "paid_maybe"
    assert_rejected(db, "ck_orders_status_valid")


def test_order_with_unknown_shipping_method_is_rejected(db: Session) -> None:
    order = make_order(db)
    order.shipping_method = "pigeon"
    # Both checks reject an unknown method; PostgreSQL reports whichever it evaluates first.
    assert_rejected(db, {"ck_orders_shipping_method_valid", "ck_orders_shipping_address_present"})


def test_order_paid_without_paid_at_is_rejected(db: Session) -> None:
    order = make_order(db)
    order.status = "paid"
    assert_rejected(db, "ck_orders_paid_has_paid_at")


def test_order_paid_with_paid_at_is_accepted(db: Session) -> None:
    order = make_order(db)
    order.status = "paid"
    order.paid_at = datetime.now(UTC)
    db.flush()


def test_order_shipped_without_shipped_at_is_rejected(db: Session) -> None:
    order = make_order(db)
    order.status = "shipped"
    order.paid_at = datetime.now(UTC)
    assert_rejected(db, "ck_orders_shipped_has_date")


def test_locker_order_without_locker_id_is_rejected(db: Session) -> None:
    order = make_order(db)
    order.locker_id = None
    assert_rejected(db, "ck_orders_shipping_address_present")


def test_courier_order_without_address_is_rejected(db: Session) -> None:
    order = make_order(db)
    order.shipping_method = "courier"
    order.locker_id = None
    assert_rejected(db, "ck_orders_shipping_address_present")


def test_courier_order_with_address_is_accepted(db: Session) -> None:
    make_order(
        db,
        shipping_method="courier",
        locker_id=None,
        address_line="ul. Świeczkowa 1/2",
        address_postal_code="00-001",
        address_city="Warszawa",
    )


def test_same_variant_twice_in_one_order_is_rejected(db: Session) -> None:
    variant = make_variant(db)
    order = make_order(db, items=[(variant, 1)])
    order.items.append(
        OrderItem(
            variant_id=variant.id,
            product_name=variant.product.name,
            variant_name=variant.name,
            unit_price_grosze=variant.product.price_grosze,
            qty=1,
        )
    )
    assert_rejected(db, "uq_order_items_order_id_variant_id")


def test_duplicate_stripe_event_id_is_rejected(db: Session) -> None:
    db.add(StripeEvent(id="evt_test_1", type="checkout.session.completed"))
    db.flush()
    db.add(StripeEvent(id="evt_test_1", type="checkout.session.completed"))
    assert_rejected(db, "pk_stripe_events")


def test_deleting_product_with_variants_is_rejected(db: Session) -> None:
    variant = make_variant(db)
    assert_rejected(
        db,
        "fk_variants_product_id_products",
        lambda: db.execute(delete(Product).where(Product.id == variant.product_id)),
    )


def test_deleting_variant_keeps_order_item_copy(db: Session) -> None:
    # Current schema: the item survives with variant_id = NULL. 6.2 must handle this when
    # returning stock (see "Pomysły na później" in ROADMAP).
    variant = make_variant(db)
    order = make_order(db, items=[(variant, 2)])

    db.delete(variant)
    db.flush()
    db.refresh(order)

    assert order.items[0].variant_id is None
    assert order.items[0].qty == 2
