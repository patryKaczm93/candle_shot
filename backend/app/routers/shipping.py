import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import ShippingMethodOut, ShippingOut
from app.services import shipping

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/shipping")
def get_shipping(db: Annotated[Session, Depends(get_db)]) -> ShippingOut:
    try:
        settings = shipping.get_shipping_settings(db)
    except shipping.ShippingSettingsError:
        logger.exception("Shipping settings are misconfigured")
        raise HTTPException(status_code=503, detail="Ustawienia dostawy są niedostępne") from None

    return ShippingOut(
        methods=[
            ShippingMethodOut(id=method, name=name, price_grosze=settings.price_grosze(method))
            for method, name in shipping.METHOD_NAMES.items()
        ],
        free_shipping_threshold_grosze=settings.free_threshold_grosze,
    )
