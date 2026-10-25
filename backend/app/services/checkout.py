import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import stripe
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, contains_eager

from app.config import settings
from app.models import Order, OrderItem, Product, Variant, generate_order_number
from app.schemas import CheckoutIn, CourierShippingIn
from app.services.orders import OrderLine, calculate_totals
from app.services.shipping import METHOD_NAMES, get_shipping_settings, shipping_cost_grosze

logger = logging.getLogger(__name__)

# Stripe accepts 30 min – 24 h after the session is created; the extra minute covers request time.
SESSION_LIFETIME = timedelta(minutes=31)
# Stripe's minimum charge in PLN.
STRIPE_MIN_AMOUNT_GROSZE = 200
ORDER_NUMBER_ATTEMPTS = 5
# Row locks are held during the Stripe call: fail fast instead of the SDK's default 80 s.
STRIPE_TIMEOUT_SECONDS = 10


class CheckoutError(Exception):
    """Checkout cannot continue; nothing has been saved."""


class ItemsUnavailableError(CheckoutError):
    def __init__(self, variant_ids: list[int]) -> None:
        super().__init__(f"unavailable variants: {variant_ids}")
        self.variant_ids = variant_ids


class AmountTooLowError(CheckoutError):
    pass


class PaymentProviderError(CheckoutError):
    pass


def get_stripe_client() -> stripe.StripeClient:
    if not settings.stripe_secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY is not set")
    return stripe.StripeClient(
        settings.stripe_secret_key,
        http_client=stripe.RequestsClient(timeout=STRIPE_TIMEOUT_SECONDS),
        # Retries reuse the idempotency key, so they never create a second session.
        max_network_retries=1,
    )


def create_checkout(db: Session, data: CheckoutIn, client: stripe.StripeClient) -> str:
    """Creates a pending order, reserves stock and opens a Stripe Checkout Session.

    One transaction: if anything fails (stock, settings, Stripe), nothing is saved and the
    reservation is undone. Returns the Checkout URL.
    """
    session: stripe.checkout.Session | None = None
    try:
        order = _create_pending_order(db, data)
        session = _create_stripe_session(client, order)
        _check_session_total(session, order)
        order.stripe_session_id = session.id
        db.commit()
    except BaseException:
        db.rollback()
        # The order is gone, so the session must not stay payable.
        if session is not None:
            _expire_session(client, session.id)
        raise
    return session.url


def _create_pending_order(db: Session, data: CheckoutIn) -> Order:
    qty_by_variant = {item.variant_id: item.qty for item in data.items}

    # FOR UPDATE, in id order (no deadlocks): a second buyer of the last piece waits for this
    # transaction and then sees the reduced stock.
    variants = db.scalars(
        select(Variant)
        .join(Variant.product)
        .options(contains_eager(Variant.product))
        .where(Variant.id.in_(qty_by_variant), Product.is_active.is_(True))
        .order_by(Variant.id)
        .with_for_update(of=Variant)
        # Read stock again from the locked rows, even if this session loaded them before.
        .execution_options(populate_existing=True)
    ).all()
    by_id = {variant.id: variant for variant in variants}

    unavailable = [
        variant_id
        for variant_id, qty in qty_by_variant.items()
        if variant_id not in by_id or by_id[variant_id].stock < qty
    ]
    if unavailable:
        raise ItemsUnavailableError(unavailable)

    # Prices only from the database.
    lines = [
        OrderLine(by_id[item.variant_id].product.price_grosze, item.qty) for item in data.items
    ]
    subtotal = calculate_totals(lines, 0).subtotal_grosze
    shipping_settings = get_shipping_settings(db)
    shipping = shipping_cost_grosze(shipping_settings, data.shipping.method, subtotal)
    totals = calculate_totals(lines, shipping)
    if totals.total_grosze < STRIPE_MIN_AMOUNT_GROSZE:
        raise AmountTooLowError()

    order = Order(
        status="pending",
        email=data.email,
        phone=data.phone,
        full_name=data.full_name,
        terms_accepted_at=datetime.now(UTC),
        shipping_method=data.shipping.method,
        subtotal_grosze=totals.subtotal_grosze,
        shipping_grosze=totals.shipping_grosze,
        total_grosze=totals.total_grosze,
        items=[
            OrderItem(
                variant_id=item.variant_id,
                product_name=by_id[item.variant_id].product.name,
                variant_name=by_id[item.variant_id].name,
                unit_price_grosze=by_id[item.variant_id].product.price_grosze,
                qty=item.qty,
            )
            for item in data.items
        ],
    )
    if isinstance(data.shipping, CourierShippingIn):
        order.address_line = data.shipping.address_line
        order.address_postal_code = data.shipping.postal_code
        order.address_city = data.shipping.city
    else:
        order.locker_id = data.shipping.locker_id
    if data.invoice:
        order.invoice_nip = data.invoice.nip
        order.invoice_name = data.invoice.name

    _insert_with_unique_number(db, order)

    for item in data.items:
        by_id[item.variant_id].stock -= item.qty
    db.flush()
    return order


def _insert_with_unique_number(db: Session, order: Order) -> None:
    """Random numbers can collide (31^6 codes); retry in a savepoint instead of failing with 500."""
    for attempt in range(1, ORDER_NUMBER_ATTEMPTS + 1):
        order.number = generate_order_number()
        try:
            with db.begin_nested():
                db.add(order)
                db.flush()
            return
        except IntegrityError:
            if attempt == ORDER_NUMBER_ATTEMPTS:
                raise
            logger.warning("Order number collision, retrying (attempt %d)", attempt)


def _line_item(name: str, unit_amount: int, quantity: int) -> dict[str, Any]:
    return {
        "price_data": {
            "currency": "pln",
            "unit_amount": unit_amount,
            "product_data": {"name": name},
        },
        "quantity": quantity,
    }


def _create_stripe_session(client: stripe.StripeClient, order: Order) -> stripe.checkout.Session:
    line_items = [
        _line_item(
            f"{item.product_name} (gips: {item.variant_name})", item.unit_price_grosze, item.qty
        )
        for item in order.items
    ]
    if order.shipping_grosze > 0:
        name = f"Dostawa: {METHOD_NAMES[order.shipping_method]}"
        line_items.append(_line_item(name, order.shipping_grosze, 1))

    frontend = settings.frontend_url.rstrip("/")
    params: dict[str, Any] = {
        "mode": "payment",
        "line_items": line_items,
        "customer_email": order.email,
        "client_reference_id": order.number,
        "metadata": {"order_id": str(order.id), "order_number": order.number},
        "expires_at": int((datetime.now(UTC) + SESSION_LIFETIME).timestamp()),
        "success_url": f"{frontend}/dziekujemy?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{frontend}/zamowienie/anulowane",
        "locale": "pl",
    }
    # Payment methods (BLIK, Przelewy24, card) are enabled in the Stripe dashboard, not here.
    try:
        session = client.v1.checkout.sessions.create(
            params=params,  # type: ignore[arg-type]
            options={"idempotency_key": f"checkout-{order.number}"},
        )
    except stripe.StripeError as error:
        logger.exception("Stripe Checkout Session failed for order %s", order.number)
        raise PaymentProviderError() from error

    return session


def _check_session_total(session: stripe.checkout.Session, order: Order) -> None:
    if session.amount_total != order.total_grosze:
        logger.error(
            "Stripe total %s differs from order %s total %s",
            session.amount_total,
            order.number,
            order.total_grosze,
        )
        raise PaymentProviderError()


def _expire_session(client: stripe.StripeClient, session_id: str) -> None:
    try:
        client.v1.checkout.sessions.expire(session_id)
    except stripe.StripeError:
        # Best effort: it expires by itself after 31 min, and the webhook (6.x) finds no order.
        logger.exception("Could not expire orphaned Stripe session %s", session_id)
