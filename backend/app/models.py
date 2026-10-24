import secrets
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Predictable constraint names, so Alembic can alter or drop them later.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

ORDER_STATUSES = ("pending", "paid", "shipped", "cancelled", "refunded")
SHIPPING_METHODS = ("locker", "courier")
MAX_QTY_PER_ITEM = 10

# No 0/O, 1/I/L: the number is read aloud and retyped by customers.
ORDER_NUMBER_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
ORDER_NUMBER_LENGTH = 6


def generate_order_number() -> str:
    """Random order number like PM-7K3QX9; does not reveal how many orders exist."""
    code = "".join(secrets.choice(ORDER_NUMBER_ALPHABET) for _ in range(ORDER_NUMBER_LENGTH))
    return f"PM-{code}"


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (CheckConstraint("price_grosze > 0", name="price_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    tagline: Mapped[str] = mapped_column(String(300), server_default="")
    description: Mapped[str] = mapped_column(Text, server_default="")
    category: Mapped[str] = mapped_column(String(50), index=True)
    price_grosze: Mapped[int]
    weight_g: Mapped[int | None]
    badge: Mapped[str | None] = mapped_column(String(50))
    image: Mapped[str | None] = mapped_column(String(300))
    is_active: Mapped[bool] = mapped_column(server_default="true")
    sort_order: Mapped[int] = mapped_column(server_default="0")

    variants: Mapped[list["Variant"]] = relationship(back_populates="product")


class Variant(Base):
    """Plaster colour of a product; stock is tracked per colour."""

    __tablename__ = "variants"
    __table_args__ = (
        UniqueConstraint("product_id", "name", name="uq_variants_product_id_name"),
        CheckConstraint("stock >= 0", name="stock_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # RESTRICT: deactivate products (is_active=false) instead of deleting them,
    # otherwise stock reserved by pending orders could not be returned.
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String(100))
    hex: Mapped[str] = mapped_column(String(7))
    stock: Mapped[int] = mapped_column(server_default="0")

    product: Mapped[Product] = relationship(back_populates="variants")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(_in("status", ORDER_STATUSES), name="status_valid"),
        CheckConstraint(_in("shipping_method", SHIPPING_METHODS), name="shipping_method_valid"),
        CheckConstraint(
            "subtotal_grosze >= 0 AND shipping_grosze >= 0", name="amounts_non_negative"
        ),
        CheckConstraint("total_grosze = subtotal_grosze + shipping_grosze", name="total_is_sum"),
        CheckConstraint(
            "(shipping_method = 'locker' AND locker_id IS NOT NULL)"
            " OR (shipping_method = 'courier' AND address_line IS NOT NULL"
            " AND address_postal_code IS NOT NULL AND address_city IS NOT NULL)",
            name="shipping_address_present",
        ),
        CheckConstraint(
            "status NOT IN ('paid', 'shipped') OR paid_at IS NOT NULL", name="paid_has_paid_at"
        ),
        CheckConstraint("status <> 'shipped' OR shipped_at IS NOT NULL", name="shipped_has_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(20), unique=True, default=generate_order_number)
    status: Mapped[str] = mapped_column(String(20), server_default="pending")

    email: Mapped[str] = mapped_column(String(254))
    phone: Mapped[str] = mapped_column(String(30))
    full_name: Mapped[str] = mapped_column(String(200))
    terms_accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    shipping_method: Mapped[str] = mapped_column(String(20))
    locker_id: Mapped[str | None] = mapped_column(String(20))
    address_line: Mapped[str | None] = mapped_column(String(200))
    address_postal_code: Mapped[str | None] = mapped_column(String(10))
    address_city: Mapped[str | None] = mapped_column(String(100))

    invoice_nip: Mapped[str | None] = mapped_column(String(10))
    invoice_name: Mapped[str | None] = mapped_column(String(200))

    subtotal_grosze: Mapped[int]
    shipping_grosze: Mapped[int]
    total_grosze: Mapped[int]

    stripe_session_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    stripe_payment_intent: Mapped[str | None] = mapped_column(String(255), index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tracking_number: Mapped[str | None] = mapped_column(String(100))

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    """Copies product name and price, so later price changes do not alter old orders."""

    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint(f"qty BETWEEN 1 AND {MAX_QTY_PER_ITEM}", name="qty_in_range"),
        CheckConstraint("unit_price_grosze > 0", name="unit_price_positive"),
        # One line per variant, so the 10-per-item limit cannot be bypassed with duplicates.
        UniqueConstraint("order_id", "variant_id", name="uq_order_items_order_id_variant_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("variants.id", ondelete="SET NULL"))
    product_name: Mapped[str] = mapped_column(String(200))
    variant_name: Mapped[str] = mapped_column(String(100))
    unit_price_grosze: Mapped[int]
    qty: Mapped[int]

    order: Mapped[Order] = relationship(back_populates="items")


class StripeEvent(Base):
    """Processed webhook events; the primary key makes handling idempotent."""

    __tablename__ = "stripe_events"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    type: Mapped[str] = mapped_column(String(100))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
