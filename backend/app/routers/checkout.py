import logging
from typing import Annotated

import stripe
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import CheckoutIn, CheckoutOut
from app.services import checkout
from app.services.shipping import ShippingSettingsError

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/checkout")
def create_checkout(
    data: CheckoutIn,
    db: Annotated[Session, Depends(get_db)],
    stripe_client: Annotated[stripe.StripeClient, Depends(checkout.get_stripe_client)],
) -> CheckoutOut:
    try:
        url = checkout.create_checkout(db, data, stripe_client)
    except checkout.ItemsUnavailableError as error:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Część produktów nie jest już dostępna w wybranej ilości.",
                "unavailable_variant_ids": error.variant_ids,
            },
        ) from None
    except checkout.AmountTooLowError:
        raise HTTPException(
            status_code=422, detail="Minimalna wartość zamówienia to 2,00 zł."
        ) from None
    except ShippingSettingsError:
        logger.exception("Shipping settings are misconfigured")
        raise HTTPException(status_code=503, detail="Ustawienia dostawy są niedostępne") from None
    except checkout.PaymentProviderError:
        raise HTTPException(
            status_code=502,
            detail="Nie udało się połączyć z systemem płatności. Spróbuj ponownie za chwilę.",
        ) from None
    return CheckoutOut(url=url)
