import logging

import stripe
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

import app.db
from app.models import Order, StripeEvent

logger = logging.getLogger(__name__)

# Other types are not recorded, so they can still be replayed once they get a handler.
HANDLED_EVENTS = {
    "checkout.session.completed",
    "checkout.session.async_payment_succeeded",
}


def handle_event(event: stripe.Event) -> None:
    """Applies a verified Stripe event exactly once.

    The event record and the status change commit together: if anything fails, nothing is
    saved, the endpoint returns 500 and Stripe's retry starts over.
    """
    if event.type not in HANDLED_EVENTS:
        return

    with app.db.SessionLocal.begin() as db:
        if not _record_event(db, event):
            logger.info("Stripe event %s was already processed", event.id)
            return
        session = event.data.object
        # completed with "unpaid" (e.g. a delayed method): wait for async_payment_succeeded.
        if session.payment_status == "paid":
            _mark_paid(db, session)


def _record_event(db: Session, event: stripe.Event) -> bool:
    """Returns False if the event is a duplicate; a concurrent delivery waits for our commit."""
    inserted_id = db.scalar(
        insert(StripeEvent)
        .values(id=event.id, type=event.type)
        .on_conflict_do_nothing(index_elements=[StripeEvent.id])
        .returning(StripeEvent.id)
    )
    return inserted_id is not None


def _mark_paid(db: Session, session: stripe.checkout.Session) -> None:
    result = db.execute(
        update(Order)
        .where(Order.stripe_session_id == session.id, Order.status == "pending")
        .values(status="paid", paid_at=func.now(), stripe_payment_intent=session.payment_intent)
    )
    if result.rowcount == 1:
        return

    status = db.scalar(select(Order.status).where(Order.stripe_session_id == session.id))
    if status == "paid":
        logger.info("Order for session %s is already paid", session.id)
    elif status is None:
        # Orphaned session or `stripe trigger`: a retry would not find an order either.
        logger.error("Payment for session %s has no matching order", session.id)
    else:
        logger.error("Payment for session %s ignored: order is %s", session.id, status)
