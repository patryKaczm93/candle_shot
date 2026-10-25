import re
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator

from app.models import MAX_QTY_PER_ITEM

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


class ShippingMethodOut(BaseModel):
    id: Literal["locker", "courier"]
    name: str
    price_grosze: int


class ShippingOut(BaseModel):
    methods: list[ShippingMethodOut]
    free_shipping_threshold_grosze: int


# --- Checkout -------------------------------------------------------------------------------

EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
PHONE_PATTERN = re.compile(r"\+?[0-9]{9,15}")
LOCKER_PATTERN = re.compile(r"[A-Z0-9-]{4,20}")
POSTAL_CODE_PATTERN = re.compile(r"[0-9]{2}-[0-9]{3}")
NIP_WEIGHTS = (6, 5, 7, 2, 3, 4, 5, 6, 7)

# Strict ints: "2", 2.0 or true never become a quantity or an id.
StrictId = Annotated[int, Field(strict=True, gt=0)]
StrictQty = Annotated[int, Field(strict=True, ge=1, le=MAX_QTY_PER_ITEM)]


def _text(min_length: int, max_length: int) -> Any:
    return StringConstraints(strip_whitespace=True, min_length=min_length, max_length=max_length)


def is_valid_nip(nip: str) -> bool:
    """Polish NIP: 10 digits, the last one is a weighted checksum (mod 11, never 10)."""
    if not re.fullmatch(r"[0-9]{10}", nip):
        return False
    checksum = sum(int(d) * w for d, w in zip(nip, NIP_WEIGHTS, strict=False)) % 11
    return checksum != 10 and checksum == int(nip[9])


class CheckoutItemIn(BaseModel):
    """Only the variant and quantity: prices sent by the browser are never read."""

    variant_id: StrictId
    qty: StrictQty


class LockerShippingIn(BaseModel):
    method: Literal["locker"]
    locker_id: str

    @field_validator("locker_id")
    @classmethod
    def _locker_id(cls, value: str) -> str:
        value = value.strip().upper()
        if not LOCKER_PATTERN.fullmatch(value):
            raise ValueError("Wybierz Paczkomat z mapy")
        return value


class CourierShippingIn(BaseModel):
    method: Literal["courier"]
    address_line: Annotated[str, _text(3, 200)]
    postal_code: str
    city: Annotated[str, _text(2, 100)]

    @field_validator("postal_code")
    @classmethod
    def _postal_code(cls, value: str) -> str:
        value = value.strip()
        if not POSTAL_CODE_PATTERN.fullmatch(value):
            raise ValueError("Kod pocztowy w formacie 00-000")
        return value


class InvoiceIn(BaseModel):
    nip: str
    name: Annotated[str, _text(2, 200)]

    @field_validator("nip")
    @classmethod
    def _nip(cls, value: str) -> str:
        value = re.sub(r"[\s-]", "", value).upper().removeprefix("PL")
        if not is_valid_nip(value):
            raise ValueError("Nieprawidłowy NIP")
        return value


class CheckoutIn(BaseModel):
    email: str
    phone: str
    full_name: Annotated[str, _text(2, 200)]
    shipping: Annotated[LockerShippingIn | CourierShippingIn, Field(discriminator="method")]
    invoice: InvoiceIn | None = None
    terms_accepted: Literal[True]
    items: Annotated[list[CheckoutItemIn], Field(min_length=1, max_length=50)]

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        value = value.strip()
        if len(value) > 254 or not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Nieprawidłowy adres e-mail")
        return value

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str) -> str:
        value = re.sub(r"[\s()-]", "", value)
        if not PHONE_PATTERN.fullmatch(value):
            raise ValueError("Nieprawidłowy numer telefonu")
        return value

    @field_validator("items")
    @classmethod
    def _unique_variants(cls, items: list[CheckoutItemIn]) -> list[CheckoutItemIn]:
        # Merging duplicates could silently exceed the 10-per-item limit; the cart never sends them.
        ids = [item.variant_id for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError("Ten sam produkt występuje w koszyku kilka razy")
        return items


class CheckoutOut(BaseModel):
    url: str
