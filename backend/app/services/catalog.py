from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.models import Product, Variant
from app.schemas import Availability, ProductDetail, ProductListItem, VariantOut


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


def _product_fields(product: Product) -> dict[str, Any]:
    return {
        "slug": product.slug,
        "name": product.name,
        "tagline": product.tagline,
        "category": product.category,
        "price_grosze": product.price_grosze,
        "weight_g": product.weight_g,
        "badge": product.badge,
        "image": product.image,
        "variants": [_variant_out(v) for v in sorted(product.variants, key=lambda v: v.id)],
    }


def _active_products() -> Select[tuple[Product]]:
    return (
        select(Product).where(Product.is_active.is_(True)).options(selectinload(Product.variants))
    )


def list_products(db: Session, category: str | None = None) -> list[ProductListItem]:
    """Active products in shop order (sort_order from the mockup), optionally one category."""
    query = _active_products().order_by(Product.sort_order, Product.id)
    if category:
        query = query.where(Product.category == category)

    return [ProductListItem(**_product_fields(product)) for product in db.scalars(query)]


def get_product(db: Session, slug: str) -> ProductDetail | None:
    """Active product by slug; an inactive product is treated as missing."""
    product = db.scalar(_active_products().where(Product.slug == slug))
    if product is None:
        return None
    return ProductDetail(**_product_fields(product), description=product.description)
