import re

from seed import PLASTER_COLOURS, SEED_PRODUCTS


def test_seed_data_has_four_products_with_four_colours() -> None:
    assert len(SEED_PRODUCTS) == 4
    assert [name for name, _ in PLASTER_COLOURS] == [
        "naturalny biały",
        "terakota",
        "szałwia",
        "grafit",
    ]
    for product in SEED_PRODUCTS:
        assert len(product.stock) == len(PLASTER_COLOURS)


def test_seed_data_prices_are_positive_int_grosze() -> None:
    for product in SEED_PRODUCTS:
        assert type(product.price_grosze) is int
        assert product.price_grosze > 0


def test_seed_data_slugs_are_unique_and_url_safe() -> None:
    slugs = [product.slug for product in SEED_PRODUCTS]
    assert len(slugs) == len(set(slugs))
    assert all(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug) for slug in slugs)


def test_seed_data_covers_all_stock_states() -> None:
    stocks = [stock for product in SEED_PRODUCTS for stock in product.stock]
    assert 0 in stocks  # "Wyprzedana"
    assert 1 in stocks  # "Ostatnia sztuka"
    assert any(stock > 1 for stock in stocks)  # "Dostępna"
