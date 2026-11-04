import json
import time
from collections.abc import Iterator
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

    post_signed(webhook_client, make_event())

    with sessions() as db:
        assert db.get(Variant, variant_id).stock == 3


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
    assert order.stripe_payment_intent is None


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

    response = post_signed(webhook_client, make_event("checkout.session.expired"))

    assert response.status_code == 200
    assert load_order(sessions).status == "pending"
    assert event_count(sessions) == 0
