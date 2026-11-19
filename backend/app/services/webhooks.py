import logging
from collections.abc import Callable
from functools import partial

import stripe
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

import app.db
from app.models import Order, OrderItem, StripeEvent, Variant
from app.services import emails

logger = logging.getLogger(__name__)

SendEmail = Callable[[], None]

# Stripe sends currency codes in lowercase; checkout always creates sessions in PLN.
ORDER_CURRENCY = "pln"
CANCELLING_EVENTS = {
    "checkout.session.async_payment_failed",
    "checkout.session.expired",
}
# Other types are not recorded, so they can still be replayed once they get a handler.
HANDLED_EVENTS = {
    "checkout.session.completed",
    "checkout.session.async_payment_succeeded",
    *CANCELLING_EVENTS,
}


def handle_event(event: stripe.Event) -> None:
    """Applies a verified Stripe event exactly once.

    The event record and the status change commit together: if anything fails, nothing is
    saved, the endpoint returns 500 and Stripe's retry starts over. E-mails go out only after
    the commit, so a duplicate or rolled-back event never sends any.
    """
    if event.type not in HANDLED_EVENTS:
        return

    send_email: SendEmail | None = None
    with app.db.SessionLocal.begin() as db:
        if not _record_event(db, event):
            logger.info("Stripe event %s was already processed", event.id)
            return
        session = event.data.object
        if event.type in CANCELLING_EVENTS:
            _cancel_order(db, session)
        # completed with "unpaid" (e.g. a delayed method): wait for async_payment_succeeded.
        elif session.payment_status == "paid":
            send_email = _mark_paid(db, session)

    if send_email:
        send_email()


def _record_event(db: Session, event: stripe.Event) -> bool:
    """Returns False if the event is a duplicate; a concurrent delivery waits for our commit."""
    inserted_id = db.scalar(
        insert(StripeEvent)
        .values(id=event.id, type=event.type)
        .on_conflict_do_nothing(index_elements=[StripeEvent.id])
        .returning(StripeEvent.id)
    )
    return inserted_id is not None


def _mark_paid(db: Session, session: stripe.checkout.Session) -> SendEmail | None:
    if session.currency == ORDER_CURRENCY:
        result = db.execute(
            update(Order)
            .where(
                Order.stripe_session_id == session.id,
                Order.status == "pending",
                Order.total_grosze == session.amount_total,
            )
            .values(status="paid", paid_at=func.now(), stripe_payment_intent=session.payment_intent)
        )
        if result.rowcount == 1:
            return partial(emails.send_order_paid, session.id)

    return _note_ignored_payment(db, session)


def _note_ignored_payment(db: Session, session: stripe.checkout.Session) -> SendEmail | None:
    """The event stays recorded, so Stripe will not retry: the seller must hear about it."""
    order = db.scalar(select(Order).where(Order.stripe_session_id == session.id))
    if order is None:
        # Orphaned session or `stripe trigger`: a retry would not find an order either.
        logger.error(
            "Payment %s for session %s has no matching order", session.payment_intent, session.id
        )
        return partial(
            emails.send_seller_alert,
            f"Stripe zgłosił płatność {session.payment_intent} za sesję {session.id}, "
            "ale w sklepie nie ma takiego zamówienia. Sprawdź ją w panelu Stripe "
            "i w razie potrzeby zwróć pieniądze.",
        )
    if order.status in ("paid", "shipped"):
        # A repeated payment event for an order already paid (or already sent): nothing to do.
        logger.info("Order %s is already %s", order.number, order.status)
        return None

    # Lets the seller find the payment and refund it by hand.
    if order.stripe_payment_intent is None:
        order.stripe_payment_intent = session.payment_intent
    logger.error(
        "Payment %s for order %s ignored: order is %s, paid %s %s, order total %s",
        session.payment_intent,
        order.number,
        order.status,
        session.amount_total,
        session.currency,
        order.total_grosze,
    )
    return partial(
        emails.send_seller_alert,
        f"Płatność {session.payment_intent} za zamówienie {order.number} nie została przyjęta: "
        f"zamówienie ma status {order.status}, zapłacono {session.amount_total} "
        f"{session.currency} (w groszach), a suma zamówienia to {order.total_grosze} groszy. "
        "Sprawdź ją w panelu Stripe i w razie potrzeby zwróć pieniądze.",
    )


def _cancel_order(db: Session, session: stripe.checkout.Session) -> None:
    # Only the delivery that really cancels the order returns stock, so it cannot happen twice.
    order_id = db.scalar(
        update(Order)
        .where(Order.stripe_session_id == session.id, Order.status == "pending")
        .values(status="cancelled")
        .returning(Order.id)
    )
    if order_id is None:
        logger.info("Session %s closed: no pending order to cancel", session.id)
        return

    items = db.execute(
        # In id order, like checkout's row locks, so the two cannot deadlock.
        select(OrderItem.variant_id, OrderItem.product_name, OrderItem.variant_name, OrderItem.qty)
        .where(OrderItem.order_id == order_id)
        .order_by(OrderItem.variant_id)
    ).all()
    for variant_id, product_name, variant_name, qty in items:
        if variant_id is None:
            logger.error(
                "Stock not returned, variant was deleted: %s x %s (%s), order id %s",
                qty,
                product_name,
                variant_name,
                order_id,
            )
            continue
        db.execute(
            update(Variant).where(Variant.id == variant_id).values(stock=Variant.stock + qty)
        )
