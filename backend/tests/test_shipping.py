import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Setting
from app.services.shipping import (
    COURIER_KEY,
    FREE_THRESHOLD_KEY,
    LOCKER_KEY,
    ShippingSettings,
    shipping_cost_grosze,
)

SETTINGS = ShippingSettings(locker_grosze=1400, courier_grosze=1800, free_threshold_grosze=10000)


def add_settings(db: Session, **values: str) -> None:
    defaults = {LOCKER_KEY: "1400", COURIER_KEY: "1800", FREE_THRESHOLD_KEY: "10000"}
    for key, value in {**defaults, **values}.items():
        db.add(Setting(key=key, value=value))
    db.flush()


def test_shipping_returns_methods_and_free_threshold_in_grosze(
    client: TestClient, db: Session
) -> None:
    add_settings(db)

    response = client.get("/api/shipping")

    assert response.status_code == 200
    assert response.json() == {
        "methods": [
            {"id": "locker", "name": "Paczkomat InPost", "price_grosze": 1400},
            {"id": "courier", "name": "Kurier", "price_grosze": 1800},
        ],
        "free_shipping_threshold_grosze": 10000,
    }


def test_shipping_with_missing_setting_returns_503(client: TestClient, db: Session) -> None:
    db.add(Setting(key=LOCKER_KEY, value="1400"))
    db.flush()

    response = client.get("/api/shipping")

    assert response.status_code == 503
    assert response.json() == {"detail": "Ustawienia dostawy są niedostępne"}


@pytest.mark.parametrize(
    "bad_value",
    ["12.99", "14,00", "-100", "", "abc", "1 400", "١٤٠٠", "100001", "9" * 5000],
)
def test_shipping_with_non_grosze_setting_returns_503(
    client: TestClient, db: Session, bad_value: str
) -> None:
    add_settings(db, **{LOCKER_KEY: bad_value})

    response = client.get("/api/shipping")

    assert response.status_code == 503


def test_shipping_with_padded_or_zero_padded_setting_is_parsed(
    client: TestClient, db: Session
) -> None:
    add_settings(db, **{LOCKER_KEY: " 1400\n", COURIER_KEY: "0018"})

    methods = client.get("/api/shipping").json()["methods"]

    assert [m["price_grosze"] for m in methods] == [1400, 18]


def test_shipping_with_zero_free_threshold_returns_503(client: TestClient, db: Session) -> None:
    add_settings(db, **{FREE_THRESHOLD_KEY: "0"})

    assert client.get("/api/shipping").status_code == 503


@pytest.mark.parametrize(
    ("method", "subtotal", "expected"),
    [
        ("locker", 0, 1400),
        ("locker", 9999, 1400),
        ("courier", 9999, 1800),
        ("locker", 10000, 0),
        ("courier", 10000, 0),
        ("courier", 25000, 0),
    ],
)
def test_shipping_cost_below_and_from_threshold(method: str, subtotal: int, expected: int) -> None:
    assert shipping_cost_grosze(SETTINGS, method, subtotal) == expected  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("method", "subtotal"),
    [("pigeon", 5000), ("locker", -1), ("locker", 99.99), ("locker", True)],
)
def test_shipping_cost_with_invalid_input_raises_value_error(method: str, subtotal: object) -> None:
    with pytest.raises(ValueError):
        shipping_cost_grosze(SETTINGS, method, subtotal)  # type: ignore[arg-type]
