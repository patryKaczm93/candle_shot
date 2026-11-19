from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.factories import make_order


def test_order_by_session_pending_returns_number_and_status(
    client: TestClient, db: Session
) -> None:
    order = make_order(db, stripe_session_id="cs_test_pending")

    response = client.get("/api/orders/by-session/cs_test_pending")

    assert response.status_code == 200
    assert response.json() == {"number": order.number, "status": "pending"}


def test_order_by_session_paid_returns_paid(client: TestClient, db: Session) -> None:
    order = make_order(
        db, stripe_session_id="cs_test_paid", status="paid", paid_at=datetime.now(UTC)
    )

    response = client.get("/api/orders/by-session/cs_test_paid")

    assert response.status_code == 200
    assert response.json() == {"number": order.number, "status": "paid"}


def test_order_by_session_unknown_session_returns_404(client: TestClient, db: Session) -> None:
    make_order(db, stripe_session_id="cs_test_other")

    response = client.get("/api/orders/by-session/cs_test_missing")

    assert response.status_code == 404


def test_order_by_session_not_a_checkout_session_returns_404(
    client: TestClient, db: Session
) -> None:
    make_order(db, stripe_session_id="cs_test_x")

    for session_id in ("pi_123", "cs_test_x%20OR%201=1", "cs_test_x%27"):
        assert client.get(f"/api/orders/by-session/{session_id}").status_code == 404


def test_order_by_session_too_long_id_returns_422(client: TestClient) -> None:
    response = client.get("/api/orders/by-session/cs_" + "a" * 300)

    assert response.status_code == 422


def test_order_by_session_cancelled_returns_cancelled(client: TestClient, db: Session) -> None:
    make_order(db, stripe_session_id="cs_test_cancelled", status="cancelled")

    response = client.get("/api/orders/by-session/cs_test_cancelled")

    assert response.json()["status"] == "cancelled"


def test_order_by_session_refunded_returns_refunded(client: TestClient, db: Session) -> None:
    make_order(
        db, stripe_session_id="cs_test_refunded", status="refunded", paid_at=datetime.now(UTC)
    )

    response = client.get("/api/orders/by-session/cs_test_refunded")

    assert response.json()["status"] == "refunded"


def test_order_by_session_does_not_expose_personal_data(client: TestClient, db: Session) -> None:
    order = make_order(db, stripe_session_id="cs_test_private")

    response = client.get("/api/orders/by-session/cs_test_private")

    assert set(response.json()) == {"number", "status"}
    for private in (order.email, order.phone, order.full_name, order.locker_id):
        assert private not in response.text


def test_order_by_session_does_not_change_order(client: TestClient, db: Session) -> None:
    order = make_order(db, stripe_session_id="cs_test_readonly")

    client.get("/api/orders/by-session/cs_test_readonly")
    db.refresh(order)

    assert order.status == "pending"
    assert order.paid_at is None
