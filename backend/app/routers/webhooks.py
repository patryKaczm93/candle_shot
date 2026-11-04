import logging
from typing import Annotated

import stripe
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from app.config import settings
from app.services import webhooks

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Annotated[str | None, Header()] = None,
) -> None:
    # Async only to read the raw body: the signature covers the exact bytes Stripe sent.
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except (stripe.SignatureVerificationError, ValueError):
        logger.warning("Rejected Stripe webhook: invalid signature, payload or missing secret")
        raise HTTPException(status_code=400, detail="Invalid webhook") from None
    # Database work is synchronous, so it must not block the event loop.
    await run_in_threadpool(webhooks.handle_event, event)
