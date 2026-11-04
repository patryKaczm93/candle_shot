import json
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
import stripe
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.main import app as fastapi_app
from app.models import Order, StripeEvent, Variant
from app.services import webhooks
from tests.factories import make_order, make_variant

URL = "/api/webhooks/stripe"
SECRET = "whsec_test_secret"
SESSION_ID = "cs_test_webhook"

COMPLETED = "checkout.session.completed"
ASYNC_SUCCEEDED = "checkout.session.async_payment_succeeded"
ASYNC_FAILED = "checkout.session.async_payment_failed"
EXPIRED = "checkout.session.expired"
# make_order's default: one item at 49,00 zł + 12,99 zł shipping.
DEFAULT_TOTAL = 6199


@pytest.fixture(autouse=True)
def webhook_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "stripe_webhook_secret", SECRET)


@pytest.fixture
def sessions(committed_sessions: sessionmaker[Session]) -> sessionmaker[Session]:
    """The webhook commits through app.db.SessionLocal, so test data must be committed too."""
    return committed_sessions


@pytest.fixture
def webhook_client() -> Iterator[TestClient]:
    # Unhandled errors become a 500, as Stripe would see them.
    yield TestClient(fastapi_app, raise_server_exceptions=False)


def make_event(
    event_type: str = COMPLETED,
    event_id: str = "evt_1",
    session_id: str = SESSION_ID,
    payment_status: str = "paid",
    amount_total: int = DEFAULT_TOTAL,
    currency: str = "pln",
) -> dict[str, Any]:
    return {
        "id": event_id,
        "object": "event",
        "type": event_type,
        "data": {
            "object": {
                "id": session_id,
                "object": "checkout.session",
                "payment_status": payment_status,
                "payment_intent": "pi_test_1",
                "amount_total": amount_total,
                "currency": currency,
            }
        },
    }


def post_signed(
    client: TestClient,
    event: dict[str, Any],
    secret: str = SECRET,
    timestamp: int | None = None,
) -> Any:
    body = json.dumps(event)
    header = stripe.WebhookSignature.generate_signature_header(body, secret, timestamp)
    return client.post(URL, content=body, headers={"Stripe-Signature": header})


def create_order(sessions: sessionmaker[Session], **overrides: Any) -> None:
    with sessions.begin() as db:
        make_order(db, stripe_session_id=SESSION_ID, **overrides)


def load_order(sessions: sessionmaker[Session]) -> Order:
    with sessions() as db:
        return db.scalars(select(Order).where(Order.stripe_session_id == SESSION_ID)).one()


def variant_stock(sessions: sessionmaker[Session], variant_id: int) -> int:
    with sessions() as db:
        return db.get(Variant, variant_id).stock


def create_reserved_order(sessions: sessionmaker[Session], **overrides: Any) -> tuple[int, int]:
    """Order for 2 + 3 pieces of two variants, whose stock is already reduced to 1 and 0."""
    with sessions.begin() as db:
        first, second = make_variant(db, stock=1), make_variant(db, stock=0)
        make_order(db, items=[(first, 2), (second, 3)], stripe_session_id=SESSION_ID, **overrides)
        return first.id, second.id


def event_count(sessions: sessionmaker[Session]) -> int:
    with sessions() as db:
        return db.scalar(select(func.count()).select_from(StripeEvent)) or 0


# --- Marking orders as paid -------------------------------------------------------------------


def test_webhook_completed_paid_marks_order_paid(
    webhook_client: TestClient, sessions: sessionmaker[Session]
) -> None:
    create_order(sessions)

    response = post_signed(webhook_client, make_event())

    assert response.status_code == 200
    order = load_order(sessions)
    assert order.status == "paid"
    assert order.paid_at is not None
    assert order.stripe_payment_intent == "pi_test_1"
    with sessions() as db:
        stored = db.scalars(select(StripeEvent)).one()
    assert (stored.id, stored.type) == ("evt_1", COMPLETED)


def test_webhook_paid_does_not_change_reserved_stock(
    webhook_client: TestClient, sessions: sessionmaker[Session]
) -> None:
    with sessions.begin() as db:
        variant = make_variant(db, stock=3)
        make_order(db, items=[(variant, 2)], stripe_session_id=SESSION_ID)
        variant_id = variant.id

    post_signed(webhook_client, make_event(amount_total=11099))

    assert load_order(sessions).status == "paid"
    assert variant_stock(sessions, variant_id) == 3


def test_webhook_completed_unpaid_waits_for_async_success(
    webhook_client: TestClient, sessions: sessionmaker[Session]
) -> None:
    create_order(sessions)

    response = post_signed(webhook_client, make_event(payment_status="unpaid"))

    assert response.status_code == 200
    order = load_order(sessions)
    assert order.status == "pending"
    assert order.paid_at is None

    response = post_signed(webhook_client, make_event(ASYNC_SUCCEEDED, event_id="evt_2"))

    assert response.status_code == 200
    assert load_order(sessions).status == "paid"
    assert event_count(sessions) == 2


# --- Idempotency ------------------------------------------------------------------------------


def test_webhook_same_event_twice_second_does_nothing(
    webhook_client: TestClient, sessions: sessionmaker[Session]
) -> None:
    create_order(sessions)
    assert post_signed(webhook_client, make_event()).status_code == 200

    # If the duplicate were processed, it would mark this order as paid again.
    with sessions.begin() as db:
        db.execute(update(Order).values(status="pending", paid_at=None))

    response = post_signed(webhook_client, make_event())

    assert response.status_code == 200
    assert load_order(sessions).status == "pending"
    assert event_count(sessions) == 1


def test_webhook_failure_saves_nothing_and_retry_succeeds(
    webhook_client: TestClient,
    sessions: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_order(sessions)

    def fail(*_: Any) -> None:
        raise RuntimeError("database went away")

    with monkeypatch.context() as patch:
        patch.setattr(webhooks, "_mark_paid", fail)
        response = post_signed(webhook_client, make_event())

    # Stripe retries after a 500, so the event must not be remembered as processed.
    assert response.status_code == 500
    assert event_count(sessions) == 0
    assert load_order(sessions).status == "pending"

    assert post_signed(webhook_client, make_event()).status_code == 200
    assert load_order(sessions).status == "paid"


# --- Signature --------------------------------------------------------------------------------


def assert_rejected(response: Any, sessions: sessionmaker[Session]) -> None:
    assert response.status_code == 400
    assert load_order(sessions).status == "pending"
    assert event_count(sessions) == 0


def test_webhook_signed_with_wrong_secret_returns_400(
    webhook_client: TestClient, sessions: sessionmaker[Session]
) -> None:
    create_order(sessions)

    response = post_signed(webhook_client, make_event(), secret="whsec_attacker")

    assert_rejected(response, sessions)


def test_webhook_without_signature_returns_400(
    webhook_client: TestClient, sessions: sessionmaker[Session]
) -> None:
    create_order(sessions)

    response = webhook_client.post(URL, content=json.dumps(make_event()))

    assert_rejected(response, sessions)


def test_webhook_with_tampered_body_returns_400(
    webhook_client: TestClient, sessions: sessionmaker[Session]
) -> None:
    create_order(sessions)
    signed_body = json.dumps(make_event(payment_status="unpaid"))
    header = stripe.WebhookSignature.generate_signature_header(signed_body, SECRET)

    response = webhook_client.post(
        URL, content=json.dumps(make_event()), headers={"Stripe-Signature": header}
    )

    assert_rejected(response, sessions)


def test_webhook_with_old_timestamp_returns_400(
    webhook_client: TestClient, sessions: sessionmaker[Session]
) -> None:
    create_order(sessions)

    response = post_signed(webhook_client, make_event(), timestamp=int(time.time()) - 3600)

    assert_rejected(response, sessions)


def test_webhook_with_binary_body_returns_400(
    webhook_client: TestClient, sessions: sessionmaker[Session]
) -> None:
    create_order(sessions)

    response = webhook_client.post(URL, content=b"\xff\xfe", headers={"Stripe-Signature": "t=1"})

    assert_rejected(response, sessions)


def test_webhook_without_configured_secret_rejects_empty_key_signature(
    webhook_client: TestClient,
    sessions: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_order(sessions)
    monkeypatch.setattr(settings, "stripe_webhook_secret", "")

    # Anyone can compute an HMAC with an empty key, so this must not pass.
    response = post_signed(webhook_client, make_event(), secret="")

    assert_rejected(response, sessions)


# --- Orders that cannot become paid -----------------------------------------------------------


@pytest.mark.parametrize("status", ["cancelled", "refunded"])
def test_webhook_paid_event_does_not_revive_closed_order(
    webhook_client: TestClient, sessions: sessionmaker[Session], status: str
) -> None:
    create_order(sessions, status=status)

    response = post_signed(webhook_client, make_event())

    assert response.status_code == 200
    order = load_order(sessions)
    assert order.status == status
    assert order.paid_at is None
    # The seller needs it to find and refund a payment that arrived too late.
    assert order.stripe_payment_intent == "pi_test_1"


def test_webhook_late_payment_keeps_original_payment_intent(
    webhook_client: TestClient, sessions: sessionmaker[Session]
) -> None:
    create_order(sessions, status="refunded", stripe_payment_intent="pi_original")

    post_signed(webhook_client, make_event())

    assert load_order(sessions).stripe_payment_intent == "pi_original"


def test_webhook_second_paid_event_keeps_first_paid_at(
    webhook_client: TestClient, sessions: sessionmaker[Session]
) -> None:
    create_order(sessions)
    post_signed(webhook_client, make_event())
    first_paid_at = load_order(sessions).paid_at

    response = post_signed(webhook_client, make_event(ASYNC_SUCCEEDED, event_id="evt_2"))

    assert response.status_code == 200
    assert load_order(sessions).paid_at == first_paid_at


def test_webhook_unknown_session_returns_200_and_changes_nothing(
    webhook_client: TestClient, sessions: sessionmaker[Session]
) -> None:
    create_order(sessions)

    response = post_signed(webhook_client, make_event(session_id="cs_test_other"))

    assert response.status_code == 200
    assert load_order(sessions).status == "pending"
    assert event_count(sessions) == 1


def test_webhook_unhandled_type_is_not_recorded(
    webhook_client: TestClient, sessions: sessionmaker[Session]
) -> None:
    create_order(sessions)

    response = post_signed(webhook_client, make_event("payment_intent.created"))

    assert response.status_code == 200
    assert load_order(sessions).status == "pending"
    assert event_count(sessions) == 0


@pytest.mark.parametrize(
    ("overrides", "paid_event"),
    [
        ({"amount_total": 1}, COMPLETED),
        ({"currency": "eur"}, COMPLETED),
        ({"amount_total": 1}, ASYNC_SUCCEEDED),
    ],
)
def test_webhook_payment_not_matching_order_keeps_it_pending(
    webhook_client: TestClient,
    sessions: sessionmaker[Session],
    overrides: dict[str, Any],
    paid_event: str,
) -> None:
    create_order(sessions)

    response = post_signed(webhook_client, make_event(paid_event, **overrides))

    assert response.status_code == 200
    order = load_order(sessions)
    assert order.status == "pending"
    assert order.paid_at is None
    assert order.stripe_payment_intent == "pi_test_1"


# --- Cancelling orders and returning stock ----------------------------------------------------


@pytest.mark.parametrize("event_type", [EXPIRED, ASYNC_FAILED])
def test_webhook_session_closed_cancels_order_and_returns_stock(
    webhook_client: TestClient, sessions: sessionmaker[Session], event_type: str
) -> None:
    first_id, second_id = create_reserved_order(sessions)

    response = post_signed(webhook_client, make_event(event_type, payment_status="unpaid"))

    assert response.status_code == 200
    order = load_order(sessions)
    assert order.status == "cancelled"
    assert order.paid_at is None
    assert variant_stock(sessions, first_id) == 3
    assert variant_stock(sessions, second_id) == 3
    assert event_count(sessions) == 1


def test_webhook_expired_adds_to_current_stock(
    webhook_client: TestClient, sessions: sessionmaker[Session]
) -> None:
    first_id, _ = create_reserved_order(sessions)
    # A new batch arrives while the session is open: it must not be overwritten.
    with sessions.begin() as db:
        db.get(Variant, first_id).stock = 10

    post_signed(webhook_client, make_event(EXPIRED, payment_status="unpaid"))

    assert variant_stock(sessions, first_id) == 12


def test_webhook_same_expired_event_twice_returns_stock_once(
    webhook_client: TestClient, sessions: sessionmaker[Session]
) -> None:
    first_id, _ = create_reserved_order(sessions)

    post_signed(webhook_client, make_event(EXPIRED, payment_status="unpaid"))
    response = post_signed(webhook_client, make_event(EXPIRED, payment_status="unpaid"))

    assert response.status_code == 200
    assert variant_stock(sessions, first_id) == 3
    assert event_count(sessions) == 1


def test_webhook_two_closing_events_return_stock_once(
    webhook_client: TestClient, sessions: sessionmaker[Session]
) -> None:
    first_id, _ = create_reserved_order(sessions)

    post_signed(webhook_client, make_event(ASYNC_FAILED, payment_status="unpaid"))
    post_signed(webhook_client, make_event(EXPIRED, event_id="evt_2", payment_status="unpaid"))

    assert variant_stock(sessions, first_id) == 3
    assert event_count(sessions) == 2


@pytest.mark.parametrize("status", ["paid", "refunded"])
def test_webhook_expired_does_not_touch_settled_order(
    webhook_client: TestClient, sessions: sessionmaker[Session], status: str
) -> None:
    first_id, _ = create_reserved_order(sessions, status=status, paid_at=datetime.now(UTC))

    response = post_signed(webhook_client, make_event(EXPIRED, payment_status="unpaid"))

    assert response.status_code == 200
    assert load_order(sessions).status == status
    assert variant_stock(sessions, first_id) == 1


def test_webhook_payment_after_expiry_keeps_order_cancelled(
    webhook_client: TestClient, sessions: sessionmaker[Session]
) -> None:
    first_id, _ = create_reserved_order(sessions)
    post_signed(webhook_client, make_event(EXPIRED, payment_status="unpaid"))

    # The amount matches, so only the order's status can keep it from becoming paid.
    response = post_signed(webhook_client, make_event(event_id="evt_2", amount_total=25799))

    assert response.status_code == 200
    assert load_order(sessions).status == "cancelled"
    assert variant_stock(sessions, first_id) == 3


def test_webhook_expired_with_deleted_variant_returns_remaining_stock(
    webhook_client: TestClient, sessions: sessionmaker[Session]
) -> None:
    first_id, second_id = create_reserved_order(sessions)
    with sessions.begin() as db:
        db.delete(db.get(Variant, second_id))

    response = post_signed(webhook_client, make_event(EXPIRED, payment_status="unpaid"))

    assert response.status_code == 200
    assert load_order(sessions).status == "cancelled"
    assert variant_stock(sessions, first_id) == 3


def test_webhook_failure_during_cancel_saves_nothing_and_retry_succeeds(
    webhook_client: TestClient,
    sessions: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_id, second_id = create_reserved_order(sessions)
    event = make_event(EXPIRED, payment_status="unpaid")
    variant_updates = 0

    def update_failing_on_second_variant(table: Any) -> Any:
        nonlocal variant_updates
        if table is Variant:
            variant_updates += 1
            if variant_updates == 2:
                raise RuntimeError("database went away")
        return update(table)

    # Fails after the status change and the first variant's return: all of it must be undone,
    # or the retry would find no pending order and the second variant's stock would be lost.
    with monkeypatch.context() as patch:
        patch.setattr(webhooks, "update", update_failing_on_second_variant)
        response = post_signed(webhook_client, event)

    assert response.status_code == 500
    assert variant_updates == 2
    assert load_order(sessions).status == "pending"
    assert variant_stock(sessions, first_id) == 1
    assert variant_stock(sessions, second_id) == 0
    assert event_count(sessions) == 0

    assert post_signed(webhook_client, event).status_code == 200
    assert load_order(sessions).status == "cancelled"
    assert variant_stock(sessions, first_id) == 3
    assert variant_stock(sessions, second_id) == 3
