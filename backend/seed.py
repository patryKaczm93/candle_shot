"""Development seed data: 4 candles from the mockup, each in 4 plaster colours.

Run: uv run python seed.py

Names, taglines, badges and colours come from docs/design/mockups (Sklep, Produkt).
The mockup shows prices and weights only as placeholders ("XX zł", "[X] g"), so the
values below are TEST DATA taken from its worst-case mode. Real prices, weights and
stock are set by the shop owner in the admin panel (story 7.1).

Safe to run repeatedly: products and colours that already exist are left untouched.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Product, Variant

# Plaster colours from the Produkt mockup.
PLASTER_COLOURS: list[tuple[str, str]] = [
    ("naturalny biały", "#FFFFFF"),
    ("terakota", "#D9A27A"),
    ("szałwia", "#B9C2A4"),
    ("grafit", "#8C8178"),
]

CANDLE_DESCRIPTION = (
    "Wosk sojowy, bawełniany knot, forma z gipsu wylewana ręcznie. "
    "Gips możesz potem użyć jako osłonkę na sukulenta."
)


@dataclass(frozen=True)
class SeedProduct:
    slug: str
    name: str
    tagline: str
    description: str
    price_grosze: int
    weight_g: int
    badge: str | None
    # Stock per colour, in PLASTER_COLOURS order.
    stock: tuple[int, int, int, int]


SEED_PRODUCTS: list[SeedProduct] = [
    SeedProduct(
        slug="wanilia-i-drewno-sandalowe",
        name="Wanilia i drewno sandałowe",
        tagline="Ciepła, otulająca, na długie wieczory pod kocem.",
        description=(
            "Kremowa wanilia ociepla drzewną nutę sandałowca. Pachnie spokojnie "
            "i nienachalnie, dobrze sprawdza się w sypialni i salonie.\n\n" + CANDLE_DESCRIPTION
        ),
        price_grosze=4900,
        weight_g=180,
        badge="Bestseller",
        stock=(6, 4, 1, 0),  # covers "Ostatnia sztuka" and "Wyprzedana"
    ),
    SeedProduct(
        slug="niedzielny-poranek",
        name="Niedzielny poranek",
        tagline="Kawa i cynamon.",
        description=CANDLE_DESCRIPTION,
        price_grosze=4900,
        weight_g=180,
        badge=None,
        stock=(5, 5, 3, 2),
    ),
    SeedProduct(
        slug="figa-i-bergamotka",
        name="Figa i bergamotka",
        tagline="Świeża, owocowa.",
        description=CANDLE_DESCRIPTION,
        price_grosze=6450,
        weight_g=180,
        badge="Nowość",
        stock=(4, 2, 6, 3),
    ),
    SeedProduct(
        slug="dym-z-kominka",
        name="Dym z kominka",
        tagline="Drzewna, zimowa.",
        description=CANDLE_DESCRIPTION,
        price_grosze=3900,
        weight_g=180,
        badge=None,
        stock=(0, 0, 0, 0),  # whole product sold out
    ),
]

CATEGORY_CANDLES = "swieczki"


def seed(session: Session) -> tuple[int, int]:
    """Insert missing seed products and colours. Returns (products_added, variants_added)."""
    products_added = variants_added = 0

    for sort_order, data in enumerate(SEED_PRODUCTS, start=1):
        product = session.scalar(select(Product).where(Product.slug == data.slug))
        if product is None:
            product = Product(
                slug=data.slug,
                name=data.name,
                tagline=data.tagline,
                description=data.description,
                category=CATEGORY_CANDLES,
                price_grosze=data.price_grosze,
                weight_g=data.weight_g,
                badge=data.badge,
                sort_order=sort_order,
            )
            session.add(product)
            session.flush()
            products_added += 1

        existing = {variant.name for variant in product.variants}
        for (colour, hex_code), stock in zip(PLASTER_COLOURS, data.stock, strict=True):
            if colour not in existing:
                session.add(Variant(product=product, name=colour, hex=hex_code, stock=stock))
                variants_added += 1

    session.commit()
    return products_added, variants_added


if __name__ == "__main__":
    with SessionLocal() as db_session:
        added_products, added_variants = seed(db_session)
    print(f"Seed: dodano {added_products} produktów i {added_variants} wariantów.")
