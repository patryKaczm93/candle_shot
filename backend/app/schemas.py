from typing import Literal

from pydantic import BaseModel

# Shown as „Dostępna”, „Ostatnia sztuka”, „Wyprzedana”. Exact stock never leaves the backend.
Availability = Literal["available", "last", "sold_out"]


class VariantOut(BaseModel):
    id: int
    name: str
    hex: str
    availability: Availability


class ProductListItem(BaseModel):
    slug: str
    name: str
    tagline: str
    category: str
    price_grosze: int
    weight_g: int | None
    badge: str | None
    image: str | None
    variants: list[VariantOut]


class ProductDetail(ProductListItem):
    description: str
