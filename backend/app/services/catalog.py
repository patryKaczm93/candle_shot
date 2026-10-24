from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Product, Variant
from app.schemas import Availability, ProductListItem, VariantOut


def availability(stock: int) -> Availability:
    if stock <= 0:
        return "sold_out"
    if stock == 1:
        return "last"
    return "available"


def _variant_out(variant: Variant) -> VariantOut:
    return VariantOut(
        id=variant.id,
        name=variant.name,
        hex=variant.hex,
        availability=availability(variant.stock),
    )


def list_products(db: Session, category: str | None = None) -> list[ProductListItem]:
    """Active products in shop order (sort_order from the mockup), optionally one category."""
    query = (
        select(Product)
        .where(Product.is_active.is_(True))
        .options(selectinload(Product.variants))
        .order_by(Product.sort_order, Product.id)
    )
    if category:
        query = query.where(Product.category == category)

    return [
        ProductListItem(
            slug=product.slug,
            name=product.name,
            tagline=product.tagline,
            category=product.category,
            price_grosze=product.price_grosze,
            weight_g=product.weight_g,
            badge=product.badge,
            image=product.image,
            variants=[_variant_out(v) for v in sorted(product.variants, key=lambda v: v.id)],
        )
        for product in db.scalars(query)
    ]
