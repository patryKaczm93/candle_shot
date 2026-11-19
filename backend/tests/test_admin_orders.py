from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app import admin
from app.models import Order
from tests.factories import make_order, make_product, make_variant
from tests.test_admin import login

TO_PACK = "/admin/do-spakowania"
ALL = "/admin/zamowienia"


@pytest.fixture
def shipped_mails(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Records which orders got the 'shipped' e-mail instead of sending it."""
    numbers: list[str] = []
    monkeypatch.setattr(admin.emails, "send_order_shipped", numbers.append)
    return numbers


def create_order(
    committed_sessions: sessionmaker[Session], status: str = "paid", **overrides: Any
) -> dict[str, Any]:
    with committed_sessions() as db:
        product = make_product(db, name="Figa i bergamotka")
        variant = make_variant(db, product=product, name="szałwia")
        paid = status in ("paid", "shipped", "refunded")
        order = make_order(
            db,
            items=[(variant, 2)],
            status=status,
            paid_at=datetime.now(UTC) if paid else None,
            shipped_at=datetime.now(UTC) if status == "shipped" else None,
            **overrides,
        )
        data = {"id": order.id, "number": order.number}
        db.commit()
    return data


def load(committed_sessions: sessionmaker[Session], order_id: int) -> Order:
    with committed_sessions() as db:
        return db.get(Order, order_id)


def ship(client: TestClient, order_id: int, tracking: str) -> int:
    response = client.post(
        f"{TO_PACK}/edit/{order_id}",
        data={"tracking_number": tracking},
        follow_redirects=False,
    )
    return response.status_code


def test_to_pack_lists_only_paid_orders_with_items_and_delivery(
    admin_client: TestClient, committed_sessions: sessionmaker[Session]
) -> None:
    paid = create_order(committed_sessions)
    others = [
        create_order(committed_sessions, status=status)
        for status in ("pending", "shipped", "cancelled", "refunded")
    ]
    login(admin_client)

    page = admin_client.get(f"{TO_PACK}/list")

    assert page.status_code == 200
    assert paid["number"] in page.text
    for order in others:
        assert order["number"] not in page.text
    assert "Figa i bergamotka — szałwia × <strong>2</strong>" in page.text
    assert "Paczkomat WAW01M" in page.text
    assert "app.models" not in page.text


def test_to_pack_shows_oldest_paid_first(
    admin_client: TestClient, committed_sessions: sessionmaker[Session]
) -> None:
    newer = create_order(committed_sessions)
    older = create_order(committed_sessions)
    with committed_sessions() as db:
        db.get(Order, older["id"]).paid_at = datetime.now(UTC) - timedelta(days=2)
        db.commit()
    login(admin_client)

    page = admin_client.get(f"{TO_PACK}/list").text

    assert page.index(older["number"]) < page.index(newer["number"])


def test_shipping_order_marks_it_shipped_and_removes_it_from_list(
    admin_client: TestClient,
    committed_sessions: sessionmaker[Session],
    shipped_mails: list[str],
) -> None:
    order = create_order(committed_sessions)
    login(admin_client)

    assert ship(admin_client, order["id"], " 6800 1234 5678 ") in (302, 303)

    saved = load(committed_sessions, order["id"])
    assert saved.status == "shipped"
    assert saved.shipped_at is not None
    assert saved.tracking_number == "6800 1234 5678"
    assert shipped_mails == [order["number"]]
    assert order["number"] not in admin_client.get(f"{TO_PACK}/list").text


def test_shipping_twice_sends_one_email(
    admin_client: TestClient,
    committed_sessions: sessionmaker[Session],
    shipped_mails: list[str],
) -> None:
    order = create_order(committed_sessions)
    login(admin_client)

    assert ship(admin_client, order["id"], "123456789") in (302, 303)
    # Double click or a second tab: the order is no longer to pack.
    assert ship(admin_client, order["id"], "999999999") == 404

    assert load(committed_sessions, order["id"]).tracking_number == "123456789"
    assert shipped_mails == [order["number"]]


@pytest.mark.parametrize("tracking", ["", "   ", "abc", "----", "<script>", "x" * 101])
def test_shipping_requires_valid_tracking_number(
    admin_client: TestClient,
    committed_sessions: sessionmaker[Session],
    shipped_mails: list[str],
    tracking: str,
) -> None:
    order = create_order(committed_sessions)
    login(admin_client)

    assert ship(admin_client, order["id"], tracking) == 400

    assert load(committed_sessions, order["id"]).status == "paid"
    assert shipped_mails == []


@pytest.mark.parametrize("status", ["pending", "cancelled", "refunded"])
def test_order_that_is_not_paid_cannot_be_shipped(
    admin_client: TestClient,
    committed_sessions: sessionmaker[Session],
    shipped_mails: list[str],
    status: str,
) -> None:
    order = create_order(committed_sessions, status=status)
    login(admin_client)

    assert admin_client.get(f"{TO_PACK}/edit/{order['id']}").status_code == 404
    assert ship(admin_client, order["id"], "123456789") == 404

    assert load(committed_sessions, order["id"]).status == status
    assert shipped_mails == []


def test_shipping_without_login_changes_nothing(
    admin_client: TestClient,
    committed_sessions: sessionmaker[Session],
    shipped_mails: list[str],
) -> None:
    order = create_order(committed_sessions)

    assert ship(admin_client, order["id"], "123456789") in (302, 303)  # redirect to login

    assert load(committed_sessions, order["id"]).status == "paid"
    assert shipped_mails == []


def test_all_orders_view_is_read_only(
    admin_client: TestClient,
    committed_sessions: sessionmaker[Session],
    shipped_mails: list[str],
) -> None:
    order = create_order(committed_sessions, status="pending")
    login(admin_client)

    page = admin_client.get(f"{ALL}/list")
    assert page.status_code == 200
    assert order["number"] in page.text
    assert "Czeka na płatność" in page.text
    assert admin_client.get(f"{ALL}/details/{order['id']}").status_code == 200

    assert admin_client.get(f"{ALL}/edit/{order['id']}").status_code == 403
    assert admin_client.post(f"{ALL}/edit/{order['id']}", data={}).status_code == 403
    for view in (ALL, TO_PACK):
        assert admin_client.delete(f"{view}/delete?pks={order['id']}").status_code == 403
        assert admin_client.get(f"{view}/export/csv").status_code == 403
        assert admin_client.get(f"{view}/create").status_code == 403
    assert load(committed_sessions, order["id"]).status == "pending"


def test_order_details_show_contact_and_address_only_after_login(
    admin_client: TestClient, committed_sessions: sessionmaker[Session]
) -> None:
    order = create_order(
        committed_sessions,
        shipping_method="courier",
        locker_id=None,
        address_line="Różana 5/2",
        address_postal_code="00-001",
        address_city="Warszawa",
    )

    hidden = admin_client.get(f"{TO_PACK}/details/{order['id']}", follow_redirects=False)
    assert hidden.status_code in (302, 303)
    login(admin_client)
    page = admin_client.get(f"{TO_PACK}/details/{order['id']}").text

    assert "Kurier: Różana 5/2, 00-001 Warszawa" in page
    assert "Figa i bergamotka — szałwia × <strong>2</strong>" in page
    all_page = admin_client.get(f"{ALL}/details/{order['id']}").text
    assert "Figa i bergamotka — szałwia × <strong>2</strong>" in all_page
    assert "+48500600700" in page


def test_order_formatters_escape_customer_and_product_text(
    admin_client: TestClient, committed_sessions: sessionmaker[Session]
) -> None:
    evil = "<img src=x onerror=alert(1)>"
    with committed_sessions() as db:
        product = make_product(db, name=evil)
        variant = make_variant(db, product=product, name=evil)
        order = make_order(
            db,
            items=[(variant, 1)],
            status="paid",
            paid_at=datetime.now(UTC),
            full_name=evil,
            shipping_method="courier",
            locker_id=None,
            address_line=evil,
            address_postal_code="00-001",
            address_city=evil,
        )
        order_id = order.id
        db.commit()
    login(admin_client)

    for path in (f"{TO_PACK}/list", f"{TO_PACK}/details/{order_id}", f"{ALL}/details/{order_id}"):
        page = admin_client.get(path).text
        assert evil not in page
        assert "&lt;img src=x onerror=alert(1)&gt;" in page


def test_to_pack_details_only_for_paid_orders(
    admin_client: TestClient, committed_sessions: sessionmaker[Session]
) -> None:
    shipped = create_order(committed_sessions, status="shipped")
    login(admin_client)

    assert admin_client.get(f"{TO_PACK}/details/{shipped['id']}").status_code == 404
    assert admin_client.get(f"{ALL}/details/{shipped['id']}").status_code == 200
