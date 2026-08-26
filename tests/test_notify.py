"""Order notification emails for the studio inbox."""

from __future__ import annotations

import json
from email.message import EmailMessage

import pytest
from fastapi.testclient import TestClient

from src.db import init_schema
from src.main import app
from src.models import Order, OrderItem, format_money
from src.notify import build_order_email, mail_configured, notify_new_order
from src.seed import seed_products


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)


def _sample_order() -> Order:
    return Order(
        id=12,
        customer_name="Ada Lovelace",
        customer_email="ada@example.com",
        shipping_address="12 Engine St\nNicosia",
        total_cents=750,
        created_at="2026-08-26",
        items=[
            OrderItem(product_name="Floral Glasses Case", quantity=1, unit_price_cents=400),
        ],
        status="new",
    )


class _FakeHTTPResponse:
    def __init__(self, status: int = 200, body: bytes = b'{"success":"true"}'):
        self.status = status
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_mail_skipped_without_inbox(monkeypatch) -> None:
    monkeypatch.setenv("NOTIFY_EMAIL", "")
    assert mail_configured() is False
    assert notify_new_order(_sample_order()) is False


def test_build_order_email_includes_customer_and_totals() -> None:
    msg = build_order_email(_sample_order())
    body = msg.get_content()
    assert msg["To"] == "dimitrioupanagiotis@outlook.com"
    assert msg["Reply-To"] == "ada@example.com"
    assert "order #12" in msg["Subject"]
    assert format_money(750) in msg["Subject"]
    assert "Ada Lovelace" in body
    assert "ada@example.com" in body
    assert "Floral Glasses Case × 1" in body
    assert "€4.00" in body
    assert "€3.50" in body
    assert "€7.50" in body
    assert "/admin/orders/12" in body


def test_notify_sends_without_smtp_password(monkeypatch) -> None:
    monkeypatch.setenv("NOTIFY_EMAIL", "dimitrioupanagiotis@outlook.com")
    captured: list[tuple[str, dict]] = []

    def fake_urlopen(req, timeout=None):
        payload = json.loads(req.data.decode())
        captured.append((req.full_url, payload))
        return _FakeHTTPResponse()

    monkeypatch.setattr("src.notify.urllib.request.urlopen", fake_urlopen)
    assert mail_configured() is True
    assert notify_new_order(_sample_order()) is True
    assert len(captured) == 1
    url, payload = captured[0]
    assert url.startswith("https://formsubmit.co/ajax/")
    assert "dimitrioupanagiotis%40outlook.com" in url
    assert payload["_replyto"] == "ada@example.com"
    assert "Floral Glasses Case × 1" in payload["message"]
    assert payload["_captcha"] == "false"


def test_notify_sends_via_smtp_when_password_set(monkeypatch) -> None:
    monkeypatch.setenv("NOTIFY_EMAIL", "dimitrioupanagiotis@outlook.com")
    monkeypatch.setenv("SMTP_USER", "dimitrioupanagiotis@outlook.com")
    monkeypatch.setenv("SMTP_PASSWORD", "app-password")
    monkeypatch.setenv("SMTP_HOST", "smtp-mail.outlook.com")
    monkeypatch.setenv("SMTP_PORT", "587")

    sent: list[EmailMessage] = []

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            self.host = host
            self.port = port

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self, context=None):
            return None

        def login(self, user, password):
            assert user == "dimitrioupanagiotis@outlook.com"
            assert password == "app-password"

        def send_message(self, msg):
            sent.append(msg)

    def boom_urlopen(*args, **kwargs):
        raise AssertionError("FormSubmit should not be used when SMTP_PASSWORD is set")

    monkeypatch.setattr("src.notify.smtplib.SMTP", FakeSMTP)
    monkeypatch.setattr("src.notify.urllib.request.urlopen", boom_urlopen)
    assert notify_new_order(_sample_order()) is True
    assert len(sent) == 1
    assert sent[0]["To"] == "dimitrioupanagiotis@outlook.com"
    assert "Floral Glasses Case" in sent[0].get_content()


def test_notify_failure_does_not_raise(monkeypatch) -> None:
    monkeypatch.setenv("NOTIFY_EMAIL", "dimitrioupanagiotis@outlook.com")

    def boom_urlopen(*args, **kwargs):
        raise OSError("network down")

    monkeypatch.setattr("src.notify.urllib.request.urlopen", boom_urlopen)
    assert notify_new_order(_sample_order()) is False


def test_checkout_emails_studio(monkeypatch) -> None:
    init_schema()
    seed_products()
    mailed: list[int] = []

    def fake_notify(order):
        mailed.append(order.id)
        assert order.customer_email == "ada@example.com"
        return True

    monkeypatch.setattr("src.main.notify_new_order", fake_notify)

    client = TestClient(app)
    products = client.get("/api/products").json()
    glasses = next(p for p in products if p["slug"] == "glasses-case")
    client.post("/cart/add", data={"product_id": glasses["id"], "quantity": 1})
    checkout = client.post(
        "/checkout",
        data={
            "customer_name": "Ada Lovelace",
            "customer_email": "ada@example.com",
            "shipping_address": "12 Engine St",
        },
    )
    assert checkout.status_code == 200
    assert "Thank you" in checkout.text
    assert len(mailed) == 1
