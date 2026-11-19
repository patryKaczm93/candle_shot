import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.admin import admin_enabled, format_zloty, parse_zloty, setup_admin
from app.models import Product, Setting, Variant
from app.services.shipping import FREE_THRESHOLD_KEY, LOCKER_KEY
from tests.conftest import ADMIN_PASSWORD as PASSWORD
from tests.conftest import ADMIN_SECRET_KEY as SECRET_KEY
from tests.factories import make_variant


def login(client: TestClient, password: str = PASSWORD, username: str = "admin") -> int:
    response = client.post(
        "/admin/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )
    return response.status_code


def availability(client: TestClient, slug: str) -> str:
    product = next(p for p in client.get("/api/products").json() if p["slug"] == slug)
    return product["variants"][0]["availability"]


def make_committed_variant(
    committed_sessions: sessionmaker[Session], stock: int
) -> dict[str, str | int]:
    with committed_sessions() as db:
        variant = make_variant(db, stock=stock)
        data: dict[str, str | int] = {
            "id": variant.id,
            "product": variant.product_id,
            "name": variant.name,
            "hex": variant.hex,
            "slug": variant.product.slug,
        }
        db.commit()
    return data


def set_stock(
    client: TestClient, variant: dict[str, str | int], stock: str, seen: str | None
) -> int:
    """Submits the edit form as the browser does: new stock plus the stock the form showed."""
    data = {
        "product": str(variant["product"]),
        "name": str(variant["name"]),
        "hex": str(variant["hex"]),
        "stock": stock,
    }
    if seen is not None:
        data["stock_seen"] = seen
    response = client.post(
        f"/admin/variant/edit/{variant['id']}", data=data, follow_redirects=False
    )
    return response.status_code


def stock_of(committed_sessions: sessionmaker[Session], variant_id: object) -> int:
    with committed_sessions() as db:
        return db.get(Variant, variant_id).stock


def change_stock_in_shop(
    committed_sessions: sessionmaker[Session], variant_id: object, delta: int
) -> None:
    """What checkout (reservation) or the webhook (refund) does meanwhile."""
    with committed_sessions() as db:
        db.get(Variant, variant_id).stock += delta
        db.commit()


# --- Money ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "grosze"),
    [("49", 4900), ("49,9", 4990), ("49,90", 4990), ("49.05", 4905), (" 14,00 zł ", 1400)],
)
def test_parse_zloty_returns_whole_grosze(text: str, grosze: int) -> None:
    assert parse_zloty(text) == grosze


@pytest.mark.parametrize("text", ["", "abc", "-5", "49,999", "1e3", "49,", "1 000 000"])
def test_parse_zloty_rejects_invalid_text(text: str) -> None:
    with pytest.raises(ValueError):
        parse_zloty(text)


def test_format_zloty_shows_two_decimals() -> None:
    assert format_zloty(4990) == "49,90"
    assert format_zloty(5) == "0,05"


# --- Login ----------------------------------------------------------------------------------


def test_admin_enabled_rejects_weak_or_example_secrets() -> None:
    assert admin_enabled(PASSWORD, SECRET_KEY)
    assert not admin_enabled("", SECRET_KEY)
    assert not admin_enabled("short", SECRET_KEY)
    assert not admin_enabled("zmien-na-dlugie-losowe-haslo", SECRET_KEY)
    assert not admin_enabled(PASSWORD, "")
    assert not admin_enabled(PASSWORD, "zmien-na-dlugi-losowy-klucz-xxxxxxxxxx")


def test_admin_with_weak_password_is_not_mounted() -> None:
    test_app = FastAPI()
    setup_admin(test_app, sessionmaker(), "", "", https_only=False)

    assert TestClient(test_app).get("/admin/").status_code == 404


def test_admin_without_login_redirects_to_login(admin_client: TestClient) -> None:
    response = admin_client.get("/admin/variant/list", follow_redirects=False)

    assert response.status_code in (302, 303)
    assert "/admin/login" in response.headers["location"]


def test_admin_login_with_wrong_password_is_rejected(admin_client: TestClient) -> None:
    assert login(admin_client, password="wrong-password-123456") == 400
    assert login(admin_client, username="root") == 400
    assert admin_client.get("/admin/variant/list", follow_redirects=False).status_code in (302, 303)


def test_admin_pages_render_in_polish(
    admin_client: TestClient, committed_sessions: sessionmaker[Session]
) -> None:
    variant = make_committed_variant(committed_sessions, stock=1)
    with committed_sessions() as db:
        db.add(Setting(key=LOCKER_KEY, value="1400"))
        db.commit()
    assert login(admin_client) in (302, 303)

    stock_page = admin_client.get("/admin/variant/list")
    assert stock_page.status_code == 200
    assert "Ostatnia sztuka" in stock_page.text
    assert "Stany magazynowe" in stock_page.text
    assert "app.models" not in stock_page.text  # names, not <app.models.Product object>
    product_page = admin_client.get("/admin/product/list")
    assert product_page.status_code == 200
    assert "49,00 zł" in product_page.text
    shipping_page = admin_client.get("/admin/setting/list")
    assert shipping_page.status_code == 200
    assert "Paczkomat InPost" in shipping_page.text
    assert "14,00 zł" in shipping_page.text
    edit_page = admin_client.get(f"/admin/variant/edit/{variant['id']}")
    assert 'name="stock_seen"' in edit_page.text
    assert 'value="1"' in edit_page.text


# --- Stock ----------------------------------------------------------------------------------


def test_admin_stock_set_to_zero_shows_sold_out_in_shop_at_once(
    admin_client: TestClient, committed_sessions: sessionmaker[Session]
) -> None:
    variant = make_committed_variant(committed_sessions, stock=5)
    assert availability(admin_client, str(variant["slug"])) == "available"
    login(admin_client)

    assert set_stock(admin_client, variant, "0", seen="5") in (302, 303)

    assert stock_of(committed_sessions, variant["id"]) == 0
    assert availability(admin_client, str(variant["slug"])) == "sold_out"


def test_admin_stock_changed_by_purchase_while_form_was_open_is_rejected(
    admin_client: TestClient, committed_sessions: sessionmaker[Session]
) -> None:
    variant = make_committed_variant(committed_sessions, stock=5)
    login(admin_client)
    # The owner opened the form at 5, then a customer reserved 2.
    change_stock_in_shop(committed_sessions, variant["id"], -2)

    for typed in ("8", "0"):
        assert set_stock(admin_client, variant, typed, seen="5") == 400

    # The reservation is kept; the owner must look at the current stock again.
    assert stock_of(committed_sessions, variant["id"]) == 3


def test_admin_stock_form_saved_twice_is_applied_once(
    admin_client: TestClient, committed_sessions: sessionmaker[Session]
) -> None:
    variant = make_committed_variant(committed_sessions, stock=5)
    login(admin_client)

    assert set_stock(admin_client, variant, "8", seen="5") in (302, 303)
    # Double click, Back button or a second tab sends the same form again.
    assert set_stock(admin_client, variant, "8", seen="5") == 400

    assert stock_of(committed_sessions, variant["id"]) == 8


def test_admin_edit_with_unchanged_stock_keeps_current_stock(
    admin_client: TestClient, committed_sessions: sessionmaker[Session]
) -> None:
    variant = make_committed_variant(committed_sessions, stock=4)
    login(admin_client)
    change_stock_in_shop(committed_sessions, variant["id"], -3)

    # Only the name or colour was edited; the stock field still shows the old 4.
    assert set_stock(admin_client, variant, "4", seen="4") in (302, 303)

    assert stock_of(committed_sessions, variant["id"]) == 1


@pytest.mark.parametrize(
    ("stock", "seen"),
    [
        ("-1", "3"),
        ("1.5", "3"),
        ("", "3"),
        ("20000", "3"),
        ("2", None),
        ("2", "³"),
        ("2", "9" * 30),
    ],
)
def test_admin_invalid_stock_is_rejected(
    admin_client: TestClient,
    committed_sessions: sessionmaker[Session],
    stock: str,
    seen: str | None,
) -> None:
    variant = make_committed_variant(committed_sessions, stock=3)
    login(admin_client)

    assert set_stock(admin_client, variant, stock, seen=seen) == 400

    assert stock_of(committed_sessions, variant["id"]) == 3


def test_admin_edit_without_login_changes_nothing(
    admin_client: TestClient, committed_sessions: sessionmaker[Session]
) -> None:
    variant = make_committed_variant(committed_sessions, stock=3)

    assert set_stock(admin_client, variant, "0", seen="3") in (302, 303)  # redirect to login

    assert stock_of(committed_sessions, variant["id"]) == 3


# --- Products -------------------------------------------------------------------------------


def test_admin_product_price_in_zloty_is_saved_as_grosze(
    admin_client: TestClient, committed_sessions: sessionmaker[Session]
) -> None:
    variant = make_committed_variant(committed_sessions, stock=1)
    login(admin_client)
    form = {
        "name": "Świeczka testowa",
        "price_grosze": "52,90",
        "is_active": "y",
        "category": "swieczki",
        "badge": "",
        "tagline": "",
        "description": "",
        "weight_g": "180",
        "image": "",
        "slug": str(variant["slug"]),
        "sort_order": "0",
    }

    response = admin_client.post(
        f"/admin/product/edit/{variant['product']}", data=form, follow_redirects=False
    )
    assert response.status_code in (302, 303)
    with committed_sessions() as db:
        assert db.get(Product, variant["product"]).price_grosze == 5290

    for bad in ("abc", "-1", "0", "49,999", "20000"):
        bad_response = admin_client.post(
            f"/admin/product/edit/{variant['product']}",
            data={**form, "price_grosze": bad},
            follow_redirects=False,
        )
        assert bad_response.status_code == 400
    with committed_sessions() as db:
        assert db.get(Product, variant["product"]).price_grosze == 5290


# --- Shipping -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("key", "bad"),
    [
        (LOCKER_KEY, "14,999"),
        (LOCKER_KEY, "-5"),
        (LOCKER_KEY, "abc"),
        (LOCKER_KEY, ""),
        (LOCKER_KEY, "1000,01"),
        (FREE_THRESHOLD_KEY, "0"),
    ],
)
def test_admin_shipping_rejects_amounts_the_shop_cannot_read(
    admin_client: TestClient, committed_sessions: sessionmaker[Session], key: str, bad: str
) -> None:
    with committed_sessions() as db:
        db.add(Setting(key=key, value="1400"))
        db.commit()
    login(admin_client)

    response = admin_client.post(
        f"/admin/setting/edit/{key}", data={"value": bad}, follow_redirects=False
    )

    assert response.status_code == 400
    with committed_sessions() as db:
        assert db.get(Setting, key).value == "1400"


def test_admin_shipping_amount_in_zloty_is_saved_as_grosze(
    admin_client: TestClient, committed_sessions: sessionmaker[Session]
) -> None:
    with committed_sessions() as db:
        db.add(Setting(key=LOCKER_KEY, value="1400"))
        db.commit()
    login(admin_client)

    response = admin_client.post(
        f"/admin/setting/edit/{LOCKER_KEY}", data={"value": "16,50"}, follow_redirects=False
    )

    assert response.status_code in (302, 303)
    with committed_sessions() as db:
        assert db.get(Setting, LOCKER_KEY).value == "1650"


# --- Nothing can be deleted or exported ------------------------------------------------------


def test_admin_cannot_delete_or_export(
    admin_client: TestClient, committed_sessions: sessionmaker[Session]
) -> None:
    variant = make_committed_variant(committed_sessions, stock=1)
    with committed_sessions() as db:
        db.add(Setting(key=LOCKER_KEY, value="1400"))
        db.commit()
    login(admin_client)

    for path in (
        f"/admin/variant/delete?pks={variant['id']}",
        f"/admin/variant/delete?pks={variant['id']},{variant['id']}",
        f"/admin/product/delete?pks={variant['product']}",
        f"/admin/setting/delete?pks={LOCKER_KEY}",
    ):
        assert admin_client.delete(path).status_code == 403
    for view in ("product", "variant", "setting"):
        assert admin_client.get(f"/admin/{view}/export/csv").status_code == 403

    with committed_sessions() as db:
        assert db.get(Variant, variant["id"]) is not None
        assert db.get(Product, variant["product"]) is not None
        assert db.get(Setting, LOCKER_KEY) is not None


@pytest.mark.parametrize("bad_hex", ["#C97C3D\n", "red;background:url(x)", "#C97C3", "C97C3D"])
def test_admin_invalid_colour_code_is_rejected(
    admin_client: TestClient, committed_sessions: sessionmaker[Session], bad_hex: str
) -> None:
    variant = make_committed_variant(committed_sessions, stock=3)
    login(admin_client)

    response = admin_client.post(
        f"/admin/variant/edit/{variant['id']}",
        data={
            "product": str(variant["product"]),
            "name": str(variant["name"]),
            "hex": bad_hex,
            "stock": "3",
            "stock_seen": "3",
        },
        follow_redirects=False,
    )

    assert response.status_code == 400
    with committed_sessions() as db:
        assert db.get(Variant, variant["id"]).hex == variant["hex"]
