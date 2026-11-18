import json
import logging
import re
import urllib.error
import urllib.request

from sqlalchemy import select
from sqlalchemy.orm import selectinload

import app.db
from app.config import settings
from app.models import Order
from app.services.shipping import METHOD_NAMES

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"
# Sent from the webhook, so a slow mail provider must not hold up the reply to Stripe.
RESEND_TIMEOUT_SECONDS = 5
# Resend error messages may quote the recipient; addresses stay out of the logs.
EMAIL_PATTERN = re.compile(r"[^\s@<>()\"']+@[^\s@<>()\"']+")


class ResendError(Exception):
    def __init__(self, status: int, reason: str) -> None:
        super().__init__(f"Resend returned {status}: {reason}")


def send_order_paid(session_id: str) -> None:
    """Confirmation for the customer, packing details for the seller. Never raises."""
    try:
        with app.db.SessionLocal() as db:
            order = db.scalars(
                select(Order)
                .options(selectinload(Order.items))
                .where(Order.stripe_session_id == session_id)
            ).one()
    except Exception:
        logger.exception("Could not load the paid order for session %s", session_id)
        return

    # The seller first: if the mail provider is slow, this one matters more.
    messages = (
        (
            settings.shop_owner_email,
            f"Nowe zamówienie {order.number}",
            _seller_text,
            order.email,
        ),
        (
            order.email,
            f"Potwierdzenie zamówienia {order.number}",
            _customer_text,
            settings.shop_owner_email,
        ),
    )
    for to, subject, build_text, reply_to in messages:
        try:
            _send(to, subject, build_text(order), reply_to)
        except Exception:
            logger.exception("E-mail not built: %s", subject)


def send_seller_alert(text: str) -> None:
    """A problem only the seller can solve, like a payment to refund by hand. Never raises."""
    if not _send(settings.shop_owner_email, "Pachnie miło: płatność wymaga sprawdzenia", text):
        # Stripe will not retry this event, so the log is the last trace of the payment.
        logger.error("Seller alert not delivered: %s", text)


def _send(to: str, subject: str, text: str, reply_to: str = "") -> bool:
    # The webhook has already committed, so a mail failure must not make Stripe retry it.
    # Addresses stay out of the logs; the subject says which order it was.
    if not (settings.resend_api_key and settings.mail_from and to):
        logger.warning("E-mail not sent, mail settings are incomplete: %s", subject)
        return False
    try:
        _post_to_resend(to, subject, text, reply_to)
    except Exception:
        logger.exception("E-mail not sent: %s", subject)
        return False
    return True


def _post_to_resend(to: str, subject: str, text: str, reply_to: str) -> None:
    body = {"from": settings.mail_from, "to": [to], "subject": subject, "text": text}
    if reply_to:
        body["reply_to"] = reply_to
    request = urllib.request.Request(
        RESEND_URL,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
            # Python's default User-Agent can be blocked by the API's firewall.
            "User-Agent": "pachnie-milo-api",
        },
    )
    # Any status other than 2xx raises HTTPError.
    try:
        with urllib.request.urlopen(request, timeout=RESEND_TIMEOUT_SECONDS):
            pass
    except urllib.error.HTTPError as error:
        with error:
            reason = _resend_reason(error)
        raise ResendError(error.code, reason) from None


def _resend_reason(error: urllib.error.HTTPError) -> str:
    """Resend's own error name and message, e.g. an unverified domain, without e-mail addresses."""
    try:
        data = json.loads(error.read(2000))
        reason = f"{data.get('name', '')}: {data.get('message', '')}"
    except Exception:
        return "no details"
    return EMAIL_PATTERN.sub("<email>", reason)[:300]


def format_pln(grosze: int) -> str:
    return f"{grosze // 100},{grosze % 100:02d} zł"


def _summary_lines(order: Order) -> list[str]:
    lines = [
        f"{item.qty} x {item.product_name} (gips: {item.variant_name}): "
        f"{format_pln(item.unit_price_grosze * item.qty)}"
        for item in order.items
    ]
    lines.append(
        f"Dostawa ({METHOD_NAMES[order.shipping_method]}): {format_pln(order.shipping_grosze)}"
    )
    lines.append(f"Razem: {format_pln(order.total_grosze)}")
    return lines


def _delivery_lines(order: Order) -> list[str]:
    if order.shipping_method == "locker":
        return [f"Paczkomat: {order.locker_id}"]
    return [
        "Adres dostawy:",
        str(order.address_line),
        f"{order.address_postal_code} {order.address_city}",
    ]


def _invoice_lines(order: Order) -> list[str]:
    if not order.invoice_nip:
        return []
    return ["", f"Faktura: {order.invoice_name}, NIP {order.invoice_nip}"]


def _customer_text(order: Order) -> str:
    return "\n".join(
        [
            f"Dziękujemy, {order.full_name}! Otrzymaliśmy płatność za zamówienie {order.number}.",
            "",
            *_summary_lines(order),
            "",
            *_delivery_lines(order),
            *_invoice_lines(order),
            "",
            "Napiszemy do Ciebie, gdy paczka wyruszy.",
            "Masz pytanie? Po prostu odpowiedz na tę wiadomość.",
            "",
            "Pachnie miło",
        ]
    )


def _seller_text(order: Order) -> str:
    return "\n".join(
        [
            f"Opłacone zamówienie {order.number} do spakowania.",
            "",
            *_summary_lines(order),
            "",
            *_delivery_lines(order),
            *_invoice_lines(order),
            "",
            f"Klient: {order.full_name}",
            f"E-mail: {order.email}",
            f"Telefon: {order.phone}",
        ]
    )
