import re
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Setting

ShippingMethod = Literal["locker", "courier"]

LOCKER_KEY = "shipping_locker_grosze"
COURIER_KEY = "shipping_courier_grosze"
FREE_THRESHOLD_KEY = "free_shipping_threshold_grosze"

METHOD_NAMES: dict[ShippingMethod, str] = {
    "locker": "Paczkomat InPost",
    "courier": "Kurier",
}


# Sanity cap: 1000,00 zł. A typo in the admin panel must fail loudly, not reach Stripe.
MAX_SETTING_GROSZE = 100_000


class ShippingSettingsError(Exception):
    """A shipping setting is missing or is not a whole number of grosze."""


@dataclass(frozen=True)
class ShippingSettings:
    locker_grosze: int
    courier_grosze: int
    free_threshold_grosze: int

    def price_grosze(self, method: ShippingMethod) -> int:
        return self.locker_grosze if method == "locker" else self.courier_grosze


def _parse_grosze(key: str, raw: str | None, *, minimum: int = 0) -> int:
    # ASCII digits only, bounded length: "12.99", "-5", "" or "١٤٠٠" fail loudly,
    # never become a float or a guess.
    if raw is None or not re.fullmatch(r"[0-9]{1,7}", raw.strip()):
        raise ShippingSettingsError(f"setting {key!r} must be whole grosze, got {raw!r}")
    value = int(raw.strip())
    if not minimum <= value <= MAX_SETTING_GROSZE:
        raise ShippingSettingsError(f"setting {key!r} out of range: {value}")
    return value


def get_shipping_settings(db: Session) -> ShippingSettings:
    keys = (LOCKER_KEY, COURIER_KEY, FREE_THRESHOLD_KEY)
    rows = dict(db.execute(select(Setting.key, Setting.value).where(Setting.key.in_(keys))).all())
    return ShippingSettings(
        locker_grosze=_parse_grosze(LOCKER_KEY, rows.get(LOCKER_KEY)),
        courier_grosze=_parse_grosze(COURIER_KEY, rows.get(COURIER_KEY)),
        # A threshold of 0 would silently make every order ship free.
        free_threshold_grosze=_parse_grosze(
            FREE_THRESHOLD_KEY, rows.get(FREE_THRESHOLD_KEY), minimum=1
        ),
    )


def shipping_cost_grosze(
    settings: ShippingSettings, method: ShippingMethod, subtotal_grosze: int
) -> int:
    """Shipping cost for an order; free from the threshold up. The only place this rule lives."""
    if method not in METHOD_NAMES:
        raise ValueError(f"unknown shipping method {method!r}")
    if type(subtotal_grosze) is not int or subtotal_grosze < 0:
        raise ValueError("subtotal_grosze must be a non-negative int")
    if subtotal_grosze >= settings.free_threshold_grosze:
        return 0
    return settings.price_grosze(method)
