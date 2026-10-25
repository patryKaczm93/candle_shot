import threading
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import stripe
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.models import Order, Variant
from app.schemas import CheckoutIn, is_valid_nip
from app.services import checkout
from tests.conftest import FakeStripe
from tests.factories import add_shipping_settings, make_order, make_product, make_variant


def payload(items: list[dict[str, Any]], **overrides: Any) -> dict[str, Any]:
    return {
        "email": "klient@example.com",
        "phone": "500 600 700",
        "full_name": "Anna Kowalska",
        "shipping": {"method": "locker", "locker_id": "waw01m"},
        "terms_accepted": True,
        "items": items,
        **overrides,
    }


def keep(db: Session) -> None:
    """Commit test data, so a rollback inside checkout cannot also undo it (and fake a pass)."""
    db.commit()


def order_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Order)) or 0


# --- Money: prices come only from the database ----------------------------------------------


def test_checkout_with_tampered_price_uses_db_price(
    client: TestClient, db: Session, fake_stripe: FakeStripe
) -> None:
    add_shipping_settings(db)
    variant = make_variant(db, product=make_product(db, price_grosze=4900))
    item = {"variant_id": variant.id, "qty": 2, "unit_price_grosze": 1, "price_grosze": 1}

    response = client.post(
        "/api/checkout",
        json=payload([item], total_grosze=1, shipping_grosze=0, subtotal_grosze=1),
    )

    assert response.status_code == 200
    line_items = fake_stripe.sessions.calls[0]["params"]["line_items"]
    assert line_items[0]["price_data"]["unit_amount"] == 4900
    assert line_items[0]["quantity"] == 2
    order = db.scalars(select(Order)).one()
    assert (order.subtotal_grosze, order.shipping_grosze, order.total_grosze) == (9800, 1400, 11200)
    assert order.items[0].unit_price_grosze == 4900


def test_checkout_creates_pending_order_reserves_stock_and_returns_url(
    client: TestClient, db: Session, fake_stripe: FakeStripe
) -> None:
    add_shipping_settings(db)
    product = make_product(db, name="Figa i bergamotka", price_grosze=5900)
    variant = make_variant(db, product=product, name="szałwia", stock=5)

    response = client.post("/api/checkout", json=payload([{"variant_id": variant.id, "qty": 3}]))

    assert response.status_code == 200
    assert response.json() == {"url": "https://checkout.stripe.com/c/pay/cs_test_1"}
    db.refresh(variant)
    assert variant.stock == 2
    order = db.scalars(select(Order)).one()
    assert order.status == "pending"
    assert order.number.startswith("PM-")
    assert order.stripe_session_id == "cs_test_1"
    assert order.locker_id == "WAW01M"
    assert order.phone == "500600700"
    assert order.terms_accepted_at is not None
    assert [(i.product_name, i.variant_name, i.qty) for i in order.items] == [
        ("Figa i bergamotka", "szałwia", 3)
    ]
    # The internal id never leaves the backend through the response.
    assert str(order.id) not in response.text.replace("cs_test_1", "")


def test_checkout_session_has_metadata_expiry_and_return_urls(
    client: TestClient, db: Session, fake_stripe: FakeStripe
) -> None:
    add_shipping_settings(db)
    variant = make_variant(db)

    client.post("/api/checkout", json=payload([{"variant_id": variant.id, "qty": 1}]))

    call = fake_stripe.sessions.calls[0]
    params = call["params"]
    order = db.scalars(select(Order)).one()
    assert params["mode"] == "payment"
    assert params["metadata"] == {"order_id": str(order.id), "order_number": order.number}
    assert params["client_reference_id"] == order.number
    assert params["customer_email"] == "klient@example.com"
    assert params["success_url"].endswith("/dziekujemy?session_id={CHECKOUT_SESSION_ID}")
    assert params["cancel_url"].endswith("/zamowienie/anulowane")
    assert "payment_method_types" not in params
    expires_in = datetime.fromtimestamp(params["expires_at"], UTC) - datetime.now(UTC)
    assert timedelta(minutes=30) < expires_in <= timedelta(minutes=31)
    assert call["options"] == {"idempotency_key": f"checkout-{order.number}"}


def test_checkout_adds_shipping_as_separate_line_item(
    client: TestClient, db: Session, fake_stripe: FakeStripe
) -> None:
    add_shipping_settings(db, courier=1800)
    variant = make_variant(db)
    shipping = {
        "method": "courier",
        "address_line": "ul. Lipowa 5/2",
        "postal_code": "00-950",
        "city": "Warszawa",
    }

    client.post(
        "/api/checkout",
        json=payload([{"variant_id": variant.id, "qty": 1}], shipping=shipping),
    )

    line_items = fake_stripe.sessions.calls[0]["params"]["line_items"]
    assert line_items[-1]["price_data"]["unit_amount"] == 1800
    assert line_items[-1]["price_data"]["product_data"]["name"] == "Dostawa: Kurier"
    order = db.scalars(select(Order)).one()
    assert (order.address_line, order.address_postal_code, order.address_city) == (
        "ul. Lipowa 5/2",
        "00-950",
        "Warszawa",
    )


def test_checkout_above_free_threshold_skips_shipping_line(
    client: TestClient, db: Session, fake_stripe: FakeStripe
) -> None:
    add_shipping_settings(db, free_from=10000)
    variant = make_variant(db, product=make_product(db, price_grosze=5000))

    client.post("/api/checkout", json=payload([{"variant_id": variant.id, "qty": 2}]))

    line_items = fake_stripe.sessions.calls[0]["params"]["line_items"]
    assert len(line_items) == 1
    assert db.scalars(select(Order)).one().shipping_grosze == 0


# --- Stock and limits -----------------------------------------------------------------------


def test_checkout_without_enough_stock_returns_409_and_saves_nothing(
    client: TestClient, db: Session, fake_stripe: FakeStripe
) -> None:
    add_shipping_settings(db)
    in_stock = make_variant(db, stock=5)
    short = make_variant(db, stock=1)
    keep(db)

    response = client.post(
        "/api/checkout",
        json=payload([{"variant_id": in_stock.id, "qty": 1}, {"variant_id": short.id, "qty": 2}]),
    )

    assert response.status_code == 409
    assert response.json()["detail"]["unavailable_variant_ids"] == [short.id]
    assert fake_stripe.sessions.calls == []
    assert order_count(db) == 0
    db.refresh(in_stock)
    assert in_stock.stock == 5


def test_checkout_with_inactive_or_unknown_variant_returns_409(
    client: TestClient, db: Session, fake_stripe: FakeStripe
) -> None:
    add_shipping_settings(db)
    inactive = make_variant(db, product=make_product(db, is_active=False))

    response = client.post(
        "/api/checkout",
        json=payload([{"variant_id": inactive.id, "qty": 1}, {"variant_id": 999999, "qty": 1}]),
    )

    assert response.status_code == 409
    assert response.json()["detail"]["unavailable_variant_ids"] == [inactive.id, 999999]


@pytest.mark.parametrize("qty", [0, 11, -1, 2.5, "2", True])
def test_checkout_with_qty_outside_limit_returns_422(
    client: TestClient, db: Session, fake_stripe: FakeStripe, qty: Any
) -> None:
    variant = make_variant(db, stock=50)

    response = client.post("/api/checkout", json=payload([{"variant_id": variant.id, "qty": qty}]))

    assert response.status_code == 422
    assert fake_stripe.sessions.calls == []


def test_checkout_with_duplicate_variant_returns_422(
    client: TestClient, db: Session, fake_stripe: FakeStripe
) -> None:
    variant = make_variant(db, stock=50)
    items = [{"variant_id": variant.id, "qty": 10}, {"variant_id": variant.id, "qty": 10}]

    response = client.post("/api/checkout", json=payload(items))

    assert response.status_code == 422
    assert order_count(db) == 0


def test_checkout_with_empty_cart_returns_422(client: TestClient, fake_stripe: FakeStripe) -> None:
    assert client.post("/api/checkout", json=payload([])).status_code == 422


# --- Customer data --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        {"terms_accepted": False},
        {"email": "nie-email"},
        {"phone": "123"},
        {"full_name": " "},
        {"shipping": {"method": "locker", "locker_id": ""}},
        {"shipping": {"method": "courier", "address_line": "ul. Lipowa 5", "city": "Kraków"}},
        {
            "shipping": {
                "method": "courier",
                "address_line": "ul. Lipowa 5",
                "postal_code": "00950",
                "city": "Kraków",
            }
        },
        {"shipping": {"method": "drone", "locker_id": "WAW01M"}},
        {"invoice": {"nip": "1234567890", "name": "Firma"}},
    ],
)
def test_checkout_with_invalid_customer_data_returns_422(
    client: TestClient, db: Session, fake_stripe: FakeStripe, overrides: dict[str, Any]
) -> None:
    variant = make_variant(db)

    response = client.post(
        "/api/checkout", json=payload([{"variant_id": variant.id, "qty": 1}], **overrides)
    )

    assert response.status_code == 422
    assert order_count(db) == 0


def test_checkout_with_valid_nip_saves_invoice(
    client: TestClient, db: Session, fake_stripe: FakeStripe
) -> None:
    add_shipping_settings(db)
    variant = make_variant(db)
    invoice = {"nip": "PL 526-000-12-46", "name": "Pracownia Sp. z o.o."}

    response = client.post(
        "/api/checkout", json=payload([{"variant_id": variant.id, "qty": 1}], invoice=invoice)
    )

    assert response.status_code == 200
    order = db.scalars(select(Order)).one()
    assert (order.invoice_nip, order.invoice_name) == ("5260001246", "Pracownia Sp. z o.o.")


@pytest.mark.parametrize(
    ("nip", "valid"),
    [("5260001246", True), ("5260001247", False), ("123", False), ("526000124a", False)],
)
def test_nip_checksum(nip: str, valid: bool) -> None:
    assert is_valid_nip(nip) is valid


# --- Failures roll everything back ----------------------------------------------------------


def test_checkout_when_stripe_fails_returns_502_and_releases_stock(
    client: TestClient, db: Session, fake_stripe: FakeStripe
) -> None:
    add_shipping_settings(db)
    variant = make_variant(db, stock=3)
    keep(db)
    fake_stripe.sessions.error = stripe.APIConnectionError("network down")

    response = client.post("/api/checkout", json=payload([{"variant_id": variant.id, "qty": 2}]))

    assert response.status_code == 502
    assert order_count(db) == 0
    db.refresh(variant)
    assert variant.stock == 3


def test_checkout_when_stripe_total_differs_returns_502_and_expires_session(
    client: TestClient, db: Session, fake_stripe: FakeStripe
) -> None:
    add_shipping_settings(db)
    variant = make_variant(db, stock=3)
    keep(db)
    fake_stripe.sessions.amount_total_offset = -100

    response = client.post("/api/checkout", json=payload([{"variant_id": variant.id, "qty": 1}]))

    assert response.status_code == 502
    assert fake_stripe.sessions.expired == ["cs_test_1"]
    assert order_count(db) == 0
    assert db.get(Variant, variant.id).stock == 3  # type: ignore[union-attr]


def test_checkout_when_commit_fails_expires_session(
    client: TestClient, db: Session, fake_stripe: FakeStripe, monkeypatch: pytest.MonkeyPatch
) -> None:
    add_shipping_settings(db)
    variant = make_variant(db)

    def failing_commit() -> None:
        raise OperationalError("COMMIT", {}, Exception("connection lost"))

    monkeypatch.setattr(db, "commit", failing_commit)

    with pytest.raises(OperationalError):
        client.post("/api/checkout", json=payload([{"variant_id": variant.id, "qty": 1}]))

    assert fake_stripe.sessions.expired == ["cs_test_1"]


def test_checkout_with_qty_equal_to_stock_sells_out(
    client: TestClient, db: Session, fake_stripe: FakeStripe
) -> None:
    add_shipping_settings(db)
    variant = make_variant(db, stock=4)

    response = client.post("/api/checkout", json=payload([{"variant_id": variant.id, "qty": 4}]))

    assert response.status_code == 200
    db.refresh(variant)
    assert variant.stock == 0


def test_checkout_with_missing_shipping_settings_returns_503(
    client: TestClient, db: Session, fake_stripe: FakeStripe
) -> None:
    variant = make_variant(db, stock=5)
    keep(db)

    response = client.post("/api/checkout", json=payload([{"variant_id": variant.id, "qty": 1}]))

    assert response.status_code == 503
    assert fake_stripe.sessions.calls == []
    assert order_count(db) == 0
    assert db.get(Variant, variant.id).stock == 5  # type: ignore[union-attr]


def test_checkout_below_stripe_minimum_returns_422(
    client: TestClient, db: Session, fake_stripe: FakeStripe
) -> None:
    add_shipping_settings(db, locker=0)
    variant = make_variant(db, product=make_product(db, price_grosze=150))

    response = client.post("/api/checkout", json=payload([{"variant_id": variant.id, "qty": 1}]))

    assert response.status_code == 422
    assert fake_stripe.sessions.calls == []


def test_checkout_with_order_number_collision_retries(
    client: TestClient, db: Session, fake_stripe: FakeStripe, monkeypatch: pytest.MonkeyPatch
) -> None:
    add_shipping_settings(db)
    make_order(db, number="PM-AAAAAA")
    variant = make_variant(db)
    numbers = iter(["PM-AAAAAA", "PM-BBBBBB"])
    monkeypatch.setattr(checkout, "generate_order_number", lambda: next(numbers))

    response = client.post("/api/checkout", json=payload([{"variant_id": variant.id, "qty": 1}]))

    assert response.status_code == 200
    assert fake_stripe.sessions.calls[0]["params"]["client_reference_id"] == "PM-BBBBBB"


def test_checkout_without_stripe_key_never_calls_stripe(client: TestClient, db: Session) -> None:
    # No fake_stripe: the real dependency runs and must refuse an empty key.
    add_shipping_settings(db)
    variant = make_variant(db)

    with pytest.raises(RuntimeError, match="STRIPE_SECRET_KEY"):
        client.post("/api/checkout", json=payload([{"variant_id": variant.id, "qty": 1}]))


# --- Concurrency: two buyers, one last piece ------------------------------------------------


def test_checkout_two_buyers_of_last_piece_only_one_gets_it(
    committed_sessions: sessionmaker[Session],
) -> None:
    with committed_sessions() as setup:
        add_shipping_settings(setup)
        variant_id = make_variant(setup, stock=1).id
        setup.commit()

    data = CheckoutIn.model_validate(payload([{"variant_id": variant_id, "qty": 1}]))
    first_holds_lock = threading.Event()

    class SlowStripe(FakeStripe):
        """The first buyer waits inside Stripe while holding the row lock."""

        def __init__(self) -> None:
            super().__init__()
            create = self.sessions.create

            def slow_create(params: dict[str, Any], options: dict[str, Any]) -> Any:
                first_holds_lock.set()
                time.sleep(0.5)
                return create(params, options)

            self.sessions.create = slow_create  # type: ignore[method-assign]

    results: dict[str, Any] = {}

    def buy(name: str, client: Any) -> None:
        with committed_sessions() as session:
            try:
                results[name] = checkout.create_checkout(session, data, client)
            except Exception as error:  # noqa: BLE001 - the test inspects the type
                results[name] = error

    first = threading.Thread(target=buy, args=("first", SlowStripe()))
    first.start()
    assert first_holds_lock.wait(timeout=5)
    second = threading.Thread(target=buy, args=("second", FakeStripe()))
    second.start()
    first.join(timeout=10)
    second.join(timeout=10)
    assert not first.is_alive() and not second.is_alive()

    assert isinstance(results["first"], str)
    assert isinstance(results["second"], checkout.ItemsUnavailableError)
    with committed_sessions() as check:
        assert check.get(Variant, variant_id).stock == 0  # type: ignore[union-attr]
        assert order_count(check) == 1
