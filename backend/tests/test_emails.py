import io
import json
import urllib.error
from email.message import Message
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.main import app as fastapi_app
from app.services import emails, webhooks
from tests.factories import make_order, make_product, make_variant
from tests.test_webhooks import (
    ASYNC_FAILED,
    ASYNC_SUCCEEDED,
    EXPIRED,
    SESSION_ID,
    create_order,
    load_order,
    make_event,
    post_signed,
    webhook_secret,  # noqa: F401
)

OWNER = "sprzedawca@example.com"
CUSTOMER = "klient@example.com"


@pytest.fixture
def client() -> TestClient:
    return TestClient(fastapi_app, raise_server_exceptions=False)


@pytest.fixture
def sessions(committed_sessions: sessionmaker[Session]) -> sessionmaker[Session]:
    return committed_sessions


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, str]]:
    """Mail settings as in production; records messages instead of calling Resend."""
    monkeypatch.setattr(settings, "resend_api_key", "re_test")
    monkeypatch.setattr(settings, "mail_from", "sklep@example.com")
    monkeypatch.setattr(settings, "shop_owner_email", OWNER)
    messages: list[dict[str, str]] = []

    def record(to: str, subject: str, text: str, reply_to: str) -> None:
        messages.append({"to": to, "subject": subject, "text": text, "reply_to": reply_to})

    monkeypatch.setattr(emails, "_post_to_resend", record)
    return messages


def recipients(messages: list[dict[str, str]]) -> list[str]:
    return [message["to"] for message in messages]


# --- When e-mails are sent --------------------------------------------------------------------


def test_webhook_paid_order_emails_customer_and_seller(
    client: TestClient, sessions: sessionmaker[Session], sent: list[dict[str, str]]
) -> None:
    create_order(sessions)

    assert post_signed(client, make_event()).status_code == 200

    number = load_order(sessions).number
    assert recipients(sent) == [OWNER, CUSTOMER]
    seller, customer = sent
    assert number in customer["subject"]
    assert "Razem: 61,99 zł" in customer["text"]
    assert customer["reply_to"] == OWNER
    assert number in seller["subject"]
    assert seller["reply_to"] == CUSTOMER
    assert "+48500600700" in seller["text"]


def test_webhook_same_event_twice_sends_emails_once(
    client: TestClient, sessions: sessionmaker[Session], sent: list[dict[str, str]]
) -> None:
    create_order(sessions)

    post_signed(client, make_event())
    post_signed(client, make_event())

    assert recipients(sent) == [OWNER, CUSTOMER]


def test_webhook_second_paid_event_sends_no_more_emails(
    client: TestClient, sessions: sessionmaker[Session], sent: list[dict[str, str]]
) -> None:
    create_order(sessions)

    post_signed(client, make_event())
    post_signed(client, make_event(ASYNC_SUCCEEDED, event_id="evt_2"))

    assert recipients(sent) == [OWNER, CUSTOMER]


def test_webhook_async_success_as_first_paid_event_sends_emails(
    client: TestClient, sessions: sessionmaker[Session], sent: list[dict[str, str]]
) -> None:
    create_order(sessions)

    post_signed(client, make_event(payment_status="unpaid"))
    post_signed(client, make_event(ASYNC_SUCCEEDED, event_id="evt_2"))

    assert recipients(sent) == [OWNER, CUSTOMER]


def test_webhook_unpaid_completed_sends_no_email(
    client: TestClient, sessions: sessionmaker[Session], sent: list[dict[str, str]]
) -> None:
    create_order(sessions)

    post_signed(client, make_event(payment_status="unpaid"))

    assert sent == []


@pytest.mark.parametrize("event_type", [EXPIRED, ASYNC_FAILED])
def test_webhook_cancelled_order_sends_no_email(
    client: TestClient,
    sessions: sessionmaker[Session],
    sent: list[dict[str, str]],
    event_type: str,
) -> None:
    create_order(sessions)

    post_signed(client, make_event(event_type, payment_status="unpaid"))

    assert sent == []


def test_webhook_rolled_back_event_sends_no_email(
    client: TestClient,
    sessions: sessionmaker[Session],
    sent: list[dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_order(sessions)
    mark_paid = webhooks._mark_paid

    def mark_paid_then_fail(*args: Any) -> None:
        mark_paid(*args)
        raise RuntimeError("database went away")

    monkeypatch.setattr(webhooks, "_mark_paid", mark_paid_then_fail)

    assert post_signed(client, make_event()).status_code == 500
    assert load_order(sessions).status == "pending"
    assert sent == []


# --- Payments the seller must check -----------------------------------------------------------


def test_webhook_amount_mismatch_alerts_only_seller(
    client: TestClient, sessions: sessionmaker[Session], sent: list[dict[str, str]]
) -> None:
    create_order(sessions)

    post_signed(client, make_event(amount_total=1))

    number = load_order(sessions).number
    assert recipients(sent) == [OWNER]
    assert number in sent[0]["text"]
    assert "pi_test_1" in sent[0]["text"]


def test_webhook_payment_for_cancelled_order_alerts_only_seller(
    client: TestClient, sessions: sessionmaker[Session], sent: list[dict[str, str]]
) -> None:
    create_order(sessions, status="cancelled")

    post_signed(client, make_event())

    assert recipients(sent) == [OWNER]
    assert "cancelled" in sent[0]["text"]


def test_webhook_payment_without_order_alerts_seller(
    client: TestClient, sessions: sessionmaker[Session], sent: list[dict[str, str]]
) -> None:
    post_signed(client, make_event(session_id="cs_test_other"))

    assert recipients(sent) == [OWNER]
    assert "cs_test_other" in sent[0]["text"]


# --- Mail failures must not reach Stripe ------------------------------------------------------


def test_webhook_resend_failure_returns_200_and_order_stays_paid(
    client: TestClient,
    sessions: sessionmaker[Session],
    sent: list[dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_order(sessions)

    def fail(*_: Any) -> None:
        raise OSError("resend is down")

    monkeypatch.setattr(emails, "_post_to_resend", fail)

    response = post_signed(client, make_event())

    assert response.status_code == 200
    assert load_order(sessions).status == "paid"


def test_webhook_failed_customer_email_still_emails_seller(
    client: TestClient,
    sessions: sessionmaker[Session],
    sent: list[dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_order(sessions)
    delivered: list[str] = []

    def fail_for_customer(to: str, *_: Any) -> None:
        if to == CUSTOMER:
            raise OSError("rejected")
        delivered.append(to)

    monkeypatch.setattr(emails, "_post_to_resend", fail_for_customer)

    assert post_signed(client, make_event()).status_code == 200
    assert delivered == [OWNER]


def test_webhook_email_text_failure_returns_200_and_still_emails_seller(
    client: TestClient,
    sessions: sessionmaker[Session],
    sent: list[dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_order(sessions)

    def fail(_: Any) -> str:
        raise KeyError("unknown shipping method")

    monkeypatch.setattr(emails, "_customer_text", fail)

    assert post_signed(client, make_event()).status_code == 200
    assert load_order(sessions).status == "paid"
    assert recipients(sent) == [OWNER]


def test_seller_alert_not_delivered_keeps_its_text_in_the_log(
    sent: list[dict[str, str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    logged: list[str] = []

    def fail(*_: Any) -> None:
        raise OSError("resend is down")

    def record(message: str, *args: Any, **_: Any) -> None:
        logged.append(message % args)

    monkeypatch.setattr(emails, "_post_to_resend", fail)
    monkeypatch.setattr(emails.logger, "error", record)

    emails.send_seller_alert("Płatność pi_test_1 do sprawdzenia")

    assert any("pi_test_1" in line for line in logged)


def test_webhook_order_lookup_failure_for_email_returns_200(
    client: TestClient,
    sessions: sessionmaker[Session],
    sent: list[dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_order(sessions)

    def fail(_: Any) -> Any:
        raise RuntimeError("database went away")

    monkeypatch.setattr(emails, "selectinload", fail)

    assert post_signed(client, make_event()).status_code == 200
    assert load_order(sessions).status == "paid"
    assert sent == []


@pytest.mark.parametrize("missing", ["resend_api_key", "mail_from", "shop_owner_email"])
def test_send_with_incomplete_settings_skips_email(
    sent: list[dict[str, str]], monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    monkeypatch.setattr(settings, missing, "")

    emails.send_seller_alert("alert")

    assert sent == []


# --- Message content --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("grosze", "expected"),
    [(0, "0,00 zł"), (5, "0,05 zł"), (6199, "61,99 zł"), (100000, "1000,00 zł")],
)
def test_format_pln_with_grosze_returns_polish_amount(grosze: int, expected: str) -> None:
    assert emails.format_pln(grosze) == expected


def test_customer_email_lists_items_and_locker(
    sessions: sessionmaker[Session], sent: list[dict[str, str]]
) -> None:
    with sessions.begin() as db:
        product = make_product(db, name="Figa i bergamotka", price_grosze=3925)
        variant = make_variant(db, product=product, name="szałwia")
        make_order(db, items=[(variant, 2)], stripe_session_id=SESSION_ID)

    emails.send_order_paid(SESSION_ID)

    text = sent[1]["text"]
    assert "2 x Figa i bergamotka (gips: szałwia): 78,50 zł" in text
    assert "Dostawa (Paczkomat InPost): 12,99 zł" in text
    assert "Paczkomat: WAW01M" in text
    assert "Faktura" not in text


def test_customer_email_with_courier_and_invoice_shows_address_and_nip(
    sessions: sessionmaker[Session], sent: list[dict[str, str]]
) -> None:
    create_order(
        sessions,
        shipping_method="courier",
        locker_id=None,
        address_line="Różana 5/2",
        address_postal_code="00-001",
        address_city="Warszawa",
        invoice_nip="5260250274",
        invoice_name="Firma Sp. z o.o.",
    )

    emails.send_order_paid(SESSION_ID)

    text = sent[1]["text"]
    assert "Różana 5/2\n00-001 Warszawa" in text
    assert "Faktura: Firma Sp. z o.o., NIP 5260250274" in text
    assert "Paczkomat:" not in text


# --- Request to Resend ------------------------------------------------------------------------


def test_post_to_resend_sends_expected_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "resend_api_key", "re_test")
    monkeypatch.setattr(settings, "mail_from", "Pachnie miło <sklep@example.com>")
    calls: list[tuple[Any, float]] = []

    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_: Any) -> None:
            pass

    def fake_urlopen(request: Any, timeout: float) -> FakeResponse:
        calls.append((request, timeout))
        return FakeResponse()

    monkeypatch.setattr(emails.urllib.request, "urlopen", fake_urlopen)

    emails._post_to_resend(CUSTOMER, "Temat", "Treść", OWNER)

    request, timeout = calls[0]
    assert request.full_url == "https://api.resend.com/emails"
    assert request.get_method() == "POST"
    assert request.get_header("Authorization") == "Bearer re_test"
    assert timeout == emails.RESEND_TIMEOUT_SECONDS
    assert json.loads(request.data) == {
        "from": "Pachnie miło <sklep@example.com>",
        "to": [CUSTOMER],
        "subject": "Temat",
        "text": "Treść",
        "reply_to": OWNER,
    }


def test_post_to_resend_rejected_raises_reason_without_addresses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "resend_api_key", "re_test")
    monkeypatch.setattr(settings, "mail_from", "onboarding@resend.dev")
    body = json.dumps(
        {
            "statusCode": 403,
            "name": "validation_error",
            "message": f"You can only send testing emails to your own email address ({OWNER}).",
        }
    ).encode()

    def fake_urlopen(request: Any, timeout: float) -> Any:
        raise urllib.error.HTTPError(
            request.full_url, 403, "Forbidden", Message(), io.BytesIO(body)
        )

    monkeypatch.setattr(emails.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(emails.ResendError) as raised:
        emails._post_to_resend(CUSTOMER, "Temat", "Treść", OWNER)

    message = str(raised.value)
    assert "403" in message
    assert "validation_error" in message
    assert "own email address" in message
    assert OWNER not in message
    assert "<email>" in message


def test_send_with_resend_error_without_json_returns_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "resend_api_key", "re_test")
    monkeypatch.setattr(settings, "mail_from", "onboarding@resend.dev")

    def fake_urlopen(request: Any, timeout: float) -> Any:
        raise urllib.error.HTTPError(
            request.full_url, 502, "Bad Gateway", Message(), io.BytesIO(b"<html>oops</html>")
        )

    monkeypatch.setattr(emails.urllib.request, "urlopen", fake_urlopen)

    assert emails._send(CUSTOMER, "Temat", "Treść") is False
