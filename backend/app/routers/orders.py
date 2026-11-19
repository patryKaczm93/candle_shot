import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import OrderStatusOut
from app.services import orders

router = APIRouter()

# Stripe Checkout Session ids look like cs_test_... / cs_live_...
SESSION_ID_PATTERN = re.compile(r"cs_[A-Za-z0-9_]+")


@router.get("/orders/by-session/{session_id}")
def get_order_by_session(
    db: Annotated[Session, Depends(get_db)],
    session_id: Annotated[str, Path(max_length=255)],
) -> OrderStatusOut:
    """Order number and status for the thank-you page. Read-only."""
    order = None
    if SESSION_ID_PATTERN.fullmatch(session_id):
        order = orders.get_order_by_session(db, session_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono zamówienia")
    return OrderStatusOut(number=order.number, status=order.status)
