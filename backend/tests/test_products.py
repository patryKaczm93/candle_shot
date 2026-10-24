from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.factories import make_product, make_variant


def test_products_list_with_inactive_product_returns_only_active(
    client: TestClient, db: Session
) -> None:
    make_product(db, slug="aktywna")
    make_product(db, slug="ukryta", is_active=False)

    response = client.get("/api/products")

    assert response.status_code == 200
    assert [p["slug"] for p in response.json()] == ["aktywna"]


def test_products_list_is_sorted_by_sort_order(client: TestClient, db: Session) -> None:
    make_product(db, slug="trzecia", sort_order=3)
    make_product(db, slug="pierwsza", sort_order=1)
    make_product(db, slug="druga", sort_order=2)

    slugs = [p["slug"] for p in client.get("/api/products").json()]

    assert slugs == ["pierwsza", "druga", "trzecia"]


def test_products_list_with_category_returns_only_that_category(
    client: TestClient, db: Session
) -> None:
    make_product(db, slug="swieczka", category="swieczki")
    make_product(db, slug="zestaw", category="zestawy")

    response = client.get("/api/products", params={"category": "zestawy"})

    assert [p["slug"] for p in response.json()] == ["zestaw"]


def test_products_list_with_unknown_category_returns_empty_list(
    client: TestClient, db: Session
) -> None:
    make_product(db, category="swieczki")

    response = client.get("/api/products", params={"category": "swiece-do-ogrodu"})

    assert response.status_code == 200
    assert response.json() == []


def test_products_list_maps_stock_to_availability_without_exact_stock(
    client: TestClient, db: Session
) -> None:
    product = make_product(db, slug="wanilia", price_grosze=4900)
    make_variant(db, product=product, name="biały", stock=5)
    make_variant(db, product=product, name="terakota", stock=1)
    make_variant(db, product=product, name="grafit", stock=0)

    [item] = client.get("/api/products").json()

    assert item["price_grosze"] == 4900
    assert type(item["price_grosze"]) is int
    assert [(v["name"], v["availability"]) for v in item["variants"]] == [
        ("biały", "available"),
        ("terakota", "last"),
        ("grafit", "sold_out"),
    ]
    assert all("stock" not in v for v in item["variants"])
    assert "stock" not in item


def test_product_detail_with_unknown_slug_returns_404(client: TestClient) -> None:
    response = client.get("/api/products/nie-ma-takiej")

    assert response.status_code == 404
    assert response.json() == {"detail": "Nie znaleziono produktu"}


def test_product_detail_with_inactive_product_returns_404(client: TestClient, db: Session) -> None:
    make_product(db, slug="ukryta", is_active=False)

    response = client.get("/api/products/ukryta")

    assert response.status_code == 404


def test_product_detail_returns_description_and_variant_availability(
    client: TestClient, db: Session
) -> None:
    product = make_product(db, slug="wanilia", price_grosze=4900, description="Kremowa wanilia.")
    make_variant(db, product=product, name="biały", stock=5)
    make_variant(db, product=product, name="terakota", stock=1)
    make_variant(db, product=product, name="grafit", stock=0)

    response = client.get("/api/products/wanilia")

    assert response.status_code == 200
    item = response.json()
    assert item["slug"] == "wanilia"
    assert item["description"] == "Kremowa wanilia."
    assert type(item["price_grosze"]) is int
    assert [(v["name"], v["availability"]) for v in item["variants"]] == [
        ("biały", "available"),
        ("terakota", "last"),
        ("grafit", "sold_out"),
    ]
    assert all("stock" not in v for v in item["variants"])
