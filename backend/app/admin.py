"""Shop admin panel at /admin for the shop owner: stock, products and shipping prices.

Everything the owner sees is in Polish and in złoty; the database keeps whole grosze.
"""

import hmac
import logging
import re
from typing import Any

from fastapi import FastAPI
from markupsafe import Markup, escape
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import update
from sqlalchemy.orm import Session, sessionmaker
from starlette.requests import Request
from wtforms import Field, Form, HiddenField, SelectField
from wtforms.validators import InputRequired, NumberRange, Optional, Regexp
from wtforms.widgets import TextInput

from app.models import Product, Setting, Variant
from app.services.shipping import (
    COURIER_KEY,
    FREE_THRESHOLD_KEY,
    LOCKER_KEY,
    MAX_SETTING_GROSZE,
    ShippingSettingsError,
    parse_grosze,
)

logger = logging.getLogger(__name__)

ADMIN_USERNAME = "admin"
MIN_PASSWORD_LENGTH = 16
MIN_SECRET_KEY_LENGTH = 32
PLACEHOLDER_PREFIX = "zmien-na"
SESSION_MAX_AGE_S = 8 * 60 * 60

# Sanity caps: a typo in the panel must be rejected, not reach Stripe or overflow a column.
MAX_PRICE_GROSZE = 1_000_000  # 10 000,00 zł
MAX_WEIGHT_G = 100_000
MAX_STOCK = 10_000

CATEGORIES = [("swieczki", "Świeczki"), ("zestawy", "Zestawy")]
SETTING_NAMES = {
    LOCKER_KEY: "Paczkomat InPost",
    COURIER_KEY: "Kurier",
    FREE_THRESHOLD_KEY: "Darmowa dostawa od",
}


# --- Money: złoty in the panel, int grosze in the database ---------------------------------

ZLOTY_PATTERN = re.compile(r"([0-9]{1,6})(?:[.,]([0-9]{1,2}))?")


def parse_zloty(text: str) -> int:
    """'49', '49,9', '49.90' or '49,90 zł' → 4990 grosze. Parsed as text, never via float."""
    cleaned = text.strip().removesuffix("zł").strip().replace(" ", "")
    match = ZLOTY_PATTERN.fullmatch(cleaned)
    if not match:
        raise ValueError("Podaj kwotę w złotych, np. 49,00")
    whole, fraction = match.groups()
    return int(whole) * 100 + int((fraction or "0").ljust(2, "0"))


def format_zloty(grosze: int) -> str:
    """4990 → '49,90'."""
    return f"{grosze // 100},{grosze % 100:02d}"


class ZlotyField(Field):
    """Text input in złoty whose data is int grosze."""

    widget = TextInput()

    def _value(self) -> str:
        if self.raw_data:
            return str(self.raw_data[0])
        return format_zloty(self.data) if isinstance(self.data, int) else ""

    def process_formdata(self, valuelist: list[Any]) -> None:
        if not valuelist or not str(valuelist[0]).strip():
            self.data = None
            return
        try:
            self.data = parse_zloty(str(valuelist[0]))
        except ValueError:
            self.data = None
            raise


# --- Login ---------------------------------------------------------------------------------


def admin_enabled(password: str, secret_key: str) -> bool:
    """The panel can change stock and prices, so it never runs with a weak or example secret."""
    return (
        len(password) >= MIN_PASSWORD_LENGTH
        and len(secret_key) >= MIN_SECRET_KEY_LENGTH
        and not password.startswith(PLACEHOLDER_PREFIX)
        and not secret_key.startswith(PLACEHOLDER_PREFIX)
    )


def is_local_url(url: str) -> bool:
    return url.startswith(("http://localhost", "http://127.0.0.1"))


def _same(given: object, expected: str) -> bool:
    if not isinstance(given, str):
        return False
    return hmac.compare_digest(given.encode(), expected.encode())


class PasswordAuth(AuthenticationBackend):
    def __init__(self, password: str, secret_key: str, https_only: bool) -> None:
        super().__init__(
            secret_key=secret_key,
            session_cookie="pm_admin",
            max_age=SESSION_MAX_AGE_S,
            https_only=https_only,
            # The only CSRF protection: sqladmin forms have no CSRF tokens.
            same_site="strict",
        )
        self._password = password

    async def login(self, request: Request) -> bool:
        form = await request.form()
        # Evaluate both so a wrong username takes as long as a wrong password.
        username_ok = _same(form.get("username"), ADMIN_USERNAME)
        password_ok = _same(form.get("password"), self._password)
        if not (username_ok and password_ok):
            client = request.client.host if request.client else "?"
            logger.warning("Rejected admin login from %s", client)
            return False
        request.session.clear()
        request.session["admin"] = True
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return request.session.get("admin") is True


# --- Stock ---------------------------------------------------------------------------------


def stock_label(stock: int) -> str:
    """Same wording as the shop (see app.services.catalog)."""
    if stock <= 0:
        return "Wyprzedana"
    if stock == 1:
        return "Ostatnia sztuka"
    return "Dostępna"


def _stock_cell(model: Variant, _: Any) -> Markup:
    return Markup("<strong>{}</strong> szt. · {}").format(model.stock, stock_label(model.stock))


HEX_PATTERN = re.compile(r"#[0-9A-Fa-f]{6}")
STOCK_SEEN_PATTERN = re.compile(r"[0-9]{1,6}")


def _colour_cell(model: Variant, _: Any) -> Markup:
    # Only a validated colour goes into the style attribute; escape() alone does not stop CSS.
    if not HEX_PATTERN.fullmatch(model.hex):
        return Markup("{}").format(model.name)
    swatch = (
        '<span style="display:inline-block;width:12px;height:12px;border-radius:50%;'
        'border:1px solid #63391C;background:{};margin-right:6px"></span>{}'
    )
    return Markup(swatch).format(escape(model.hex), model.name)


class StockAdmin(ModelView, model=Variant):
    """Stock of each colour: what can still be sold, after reservations and paid orders.

    Checkout reserves stock with `stock = stock - qty` at any moment. The form remembers the
    stock it showed (`stock_seen`) and saves only if the database still has that value
    (compare-and-set). A purchase made while the form was open, a double click on Save or a
    form saved again from another tab is rejected instead of overwriting or doubling stock.
    """

    name = "Stan"
    name_plural = "Stany magazynowe"
    icon = "fa-solid fa-boxes-stacked"
    # Deleting a colour would detach it from pending orders and lose their reservation.
    can_delete = False
    can_export = False
    can_view_details = False
    page_size = 50
    column_list = [Variant.product, Variant.name, Variant.stock]
    column_default_sort = [(Variant.product_id, False), (Variant.id, False)]
    column_sortable_list = [Variant.stock]
    column_searchable_list = [Variant.name]
    column_formatters = {Variant.name: _colour_cell, Variant.stock: _stock_cell}
    form_columns = [Variant.product, Variant.name, Variant.hex, Variant.stock]
    column_labels = {
        Variant.product: "Świeczka",
        Variant.name: "Kolor gipsu",
        Variant.hex: "Kod koloru",
        Variant.stock: "Stan",
    }
    form_args = {
        "stock": {
            "label": "Ile sztuk możesz jeszcze sprzedać",
            "description": (
                "Nie licz sztuk już zamówionych (opłaconych albo czekających na płatność), "
                "sklep odjął je sam. 0 = „Wyprzedana”, 1 = „Ostatnia sztuka”."
            ),
            "validators": [
                InputRequired("Wpisz liczbę sztuk, np. 0"),
                NumberRange(min=0, max=MAX_STOCK, message="Od 0 do 10000 sztuk"),
            ],
        },
        "hex": {
            "description": "Kolor kropki w sklepie, np. #C97C3D.",
            "validators": [Regexp(r"^#[0-9A-Fa-f]{6}\Z", message="Format #RRGGBB, np. #C97C3D")],
        },
    }

    async def scaffold_form(self, rules: list[str] | None = None) -> type[Form]:
        form = await super().scaffold_form(rules)

        class StockForm(form):  # type: ignore[valid-type, misc]
            stock_seen = HiddenField(validators=[Optional()])

        return StockForm

    async def get_form_data_for_edit(self, obj: Any) -> dict[str, Any]:
        data = await super().get_form_data_for_edit(obj)
        data["stock_seen"] = str(obj.stock)
        return data

    async def on_model_change(
        self, data: dict[str, Any], model: Any, is_created: bool, request: Request
    ) -> None:
        new_stock = data.pop("stock")
        seen = data.pop("stock_seen", None)
        if is_created:
            model.stock = new_stock
            return
        if not isinstance(seen, str) or not STOCK_SEEN_PATTERN.fullmatch(seen):
            raise ValueError("Odśwież stronę i wpisz stan jeszcze raz.")
        old_stock = int(seen)
        if new_stock == old_stock:
            return
        # Compare-and-set: saves only if nobody changed the stock since the form was opened.
        with self.session_maker() as session:
            result = session.execute(
                update(Variant)
                .where(Variant.id == model.id, Variant.stock == old_stock)
                .values(stock=new_stock)
            )
            session.commit()
        if result.rowcount != 1:
            raise ValueError(
                "Stan zmienił się od otwarcia tego formularza (ktoś kupił albo zapisano go już "
                "wcześniej). Wróć do listy, sprawdź aktualny stan i wpisz go jeszcze raz."
            )
        logger.warning(
            "Admin changed stock of variant %s from %d to %d", model.id, old_stock, new_stock
        )


# --- Products ------------------------------------------------------------------------------


def _price_cell(model: Product, _: Any) -> str:
    return f"{format_zloty(model.price_grosze)} zł"


class ProductAdmin(ModelView, model=Product):
    name = "Produkt"
    name_plural = "Produkty"
    icon = "fa-solid fa-fire"
    # Hide instead of deleting: old orders and reservations refer to products.
    can_delete = False
    can_export = False
    can_view_details = False
    column_list = [Product.name, Product.price_grosze, Product.badge, Product.is_active]
    column_searchable_list = [Product.name]
    column_default_sort = [(Product.sort_order, False), (Product.id, False)]
    column_formatters = {Product.price_grosze: _price_cell}
    form_columns = [
        Product.name,
        Product.price_grosze,
        Product.is_active,
        Product.category,
        Product.badge,
        Product.tagline,
        Product.description,
        Product.weight_g,
        Product.image,
        Product.slug,
        Product.sort_order,
    ]
    column_labels = {
        Product.name: "Nazwa",
        Product.price_grosze: "Cena",
        Product.is_active: "Widoczny w sklepie",
        Product.category: "Kategoria",
        Product.badge: "Odznaka",
        Product.tagline: "Krótki opis (pod nazwą)",
        Product.description: "Opis",
        Product.weight_g: "Waga wosku (g)",
        Product.image: "Zdjęcie",
        Product.slug: "Adres strony",
        Product.sort_order: "Kolejność",
    }
    form_args = {
        "is_active": {
            "description": "Odznacz, żeby ukryć świeczkę w sklepie. Produktów się nie usuwa."
        },
        "badge": {"description": "Opcjonalnie, np. „Bestseller” albo „Nowość”."},
        "weight_g": {"validators": [Optional(), NumberRange(min=0, max=MAX_WEIGHT_G)]},
        "image": {"description": "Ścieżka pliku w frontend/public/img, np. /img/wanilia.webp."},
        "slug": {
            "description": "Końcówka adresu /sklep/…, np. wanilia. Nie zmieniaj po starcie.",
            "validators": [
                Regexp(
                    r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
                    message="Tylko małe litery bez polskich znaków, cyfry i myślniki",
                )
            ],
        },
        "sort_order": {"description": "Mniejsza liczba = wyżej w sklepie."},
    }

    async def scaffold_form(self, rules: list[str] | None = None) -> type[Form]:
        form = await super().scaffold_form(rules)

        class ProductForm(form):  # type: ignore[valid-type, misc]
            price_grosze = ZlotyField(
                "Cena (zł)",
                description="Np. 49,00",
                validators=[
                    InputRequired("Podaj cenę, np. 49,00"),
                    NumberRange(min=1, max=MAX_PRICE_GROSZE, message="Od 0,01 do 10 000,00 zł"),
                ],
            )
            category = SelectField("Kategoria", choices=CATEGORIES)

        return ProductForm


# --- Shipping ------------------------------------------------------------------------------


def _setting_name_cell(model: Setting, _: Any) -> str:
    return SETTING_NAMES.get(model.key, model.key)


def _setting_value_cell(model: Setting, _: Any) -> str:
    try:
        return f"{format_zloty(parse_grosze(model.key, model.value))} zł"
    except ShippingSettingsError:
        return f"BŁĄD: {model.value}"


class ShippingAdmin(ModelView, model=Setting):
    name = "Dostawa"
    name_plural = "Dostawa"
    icon = "fa-solid fa-truck"
    # The shop reads these exact keys; only their amounts may change.
    can_create = False
    can_delete = False
    can_export = False
    can_view_details = False
    column_list = [Setting.key, Setting.value]
    column_sortable_list: list[Any] = []
    column_formatters = {Setting.key: _setting_name_cell, Setting.value: _setting_value_cell}
    form_columns = [Setting.value]
    column_labels = {Setting.key: "Co", Setting.value: "Kwota"}

    async def scaffold_form(self, rules: list[str] | None = None) -> type[Form]:
        form = await super().scaffold_form(rules)

        class ShippingForm(form):  # type: ignore[valid-type, misc]
            value = ZlotyField(
                "Kwota (zł)",
                description="Np. 14,00. Darmowa dostawa musi być większa od zera.",
                validators=[InputRequired("Podaj kwotę, np. 14,00")],
            )

        return ShippingForm

    async def get_form_data_for_edit(self, obj: Any) -> dict[str, Any]:
        data = await super().get_form_data_for_edit(obj)
        try:
            data["value"] = parse_grosze(obj.key, obj.value)
        except ShippingSettingsError:
            data["value"] = None
        return data

    async def on_model_change(
        self, data: dict[str, Any], model: Any, is_created: bool, request: Request
    ) -> None:
        # Same rules as the shop reads them, so the panel cannot save a value that breaks checkout.
        minimum = 1 if model.key == FREE_THRESHOLD_KEY else 0
        grosze = data.get("value")
        if not isinstance(grosze, int) or not minimum <= grosze <= MAX_SETTING_GROSZE:
            raise ValueError(
                f"Kwota musi być od {format_zloty(minimum)} do "
                f"{format_zloty(MAX_SETTING_GROSZE)} zł."
            )
        data["value"] = str(grosze)


def setup_admin(
    app: FastAPI,
    session_maker: sessionmaker[Session],
    password: str,
    secret_key: str,
    https_only: bool,
) -> Admin | None:
    """Mounts /admin, or nothing (404) when the password or key is missing or weak."""
    if not admin_enabled(password, secret_key):
        logger.warning("Admin panel disabled: set a strong ADMIN_PASSWORD and ADMIN_SECRET_KEY")
        return None

    admin = Admin(
        app,
        session_maker=session_maker,
        title="Pachnie miło — panel",
        authentication_backend=PasswordAuth(password, secret_key, https_only),
    )
    views: list[Any] = [StockAdmin, ProductAdmin, ShippingAdmin]
    for view in views:
        admin.add_view(view)
    return admin
