"""Email the studio when a customer places an order."""

from __future__ import annotations

import json
import logging
import os
import smtplib
import ssl
import urllib.parse
import urllib.request
from email.message import EmailMessage

from src.models import Order, format_money

logger = logging.getLogger(__name__)

DEFAULT_NOTIFY_EMAIL = "dimitrioupanagiotis@outlook.com"
DEFAULT_SMTP_HOST = "smtp-mail.outlook.com"
DEFAULT_SHOP_URL = "https://print-me-maybe.onrender.com"
FORMSUBMIT_URL = "https://formsubmit.co/ajax/"


def notify_email() -> str:
    return os.environ.get("NOTIFY_EMAIL", DEFAULT_NOTIFY_EMAIL).strip()


def smtp_host() -> str:
    return os.environ.get("SMTP_HOST", DEFAULT_SMTP_HOST).strip()


def smtp_port() -> int:
    raw = os.environ.get("SMTP_PORT", "587").strip()
    try:
        return int(raw)
    except ValueError:
        return 587


def smtp_user() -> str:
    return os.environ.get("SMTP_USER", notify_email()).strip()


def smtp_password() -> str:
    return os.environ.get("SMTP_PASSWORD", "").strip()


def shop_url() -> str:
    return os.environ.get("SHOP_URL", DEFAULT_SHOP_URL).rstrip("/")


def mail_configured() -> bool:
    """True when we have an inbox to notify. No mail password is required."""
    return bool(notify_email())


def shop_name() -> str:
    return os.environ.get("SHOP_NAME", "Print Me Maybe")


def order_email_subject(order: Order) -> str:
    return f"New {shop_name()} order #{order.id} ({order.total_display})"


def order_email_body(order: Order) -> str:
    shipping = (
        "Free" if order.shipping_cents == 0 else format_money(order.shipping_cents)
    )
    lines = [
        f"New order #{order.id} — {shop_name()}",
        "",
        "Customer",
        f"Name: {order.customer_name}",
        f"Email: {order.customer_email}",
        "Address:",
        order.shipping_address,
        "",
        "Items",
    ]
    for item in order.items:
        lines.append(
            f"- {item.product_name} × {item.quantity} — {item.line_total_display}"
        )
    lines.extend(
        [
            "",
            f"Subtotal: {format_money(order.subtotal_cents)}",
            f"Shipping: {shipping}",
            f"Total: {order.total_display}",
            "",
            "No payment was collected at checkout.",
            "",
            "Open in studio:",
            f"{shop_url()}/admin/orders/{order.id}",
            "",
        ]
    )
    return "\n".join(lines)


def build_order_email(order: Order) -> EmailMessage:
    """Plain-text studio alert with Reply-To set to the customer."""
    msg = EmailMessage()
    msg["Subject"] = order_email_subject(order)
    msg["From"] = smtp_user() or notify_email()
    msg["To"] = notify_email()
    msg["Reply-To"] = order.customer_email
    msg.set_content(order_email_body(order))
    return msg


def _send_via_smtp(msg: EmailMessage) -> None:
    host = smtp_host()
    port = smtp_port()
    user = smtp_user()
    password = smtp_password()
    context = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=15, context=context) as smtp:
            smtp.login(user, password)
            smtp.send_message(msg)
        return
    with smtplib.SMTP(host, port, timeout=15) as smtp:
        smtp.starttls(context=context)
        smtp.login(user, password)
        smtp.send_message(msg)


def _send_via_formsubmit(order: Order) -> None:
    """Forward the order through FormSubmit — no inbox password needed."""
    payload = {
        "_subject": order_email_subject(order),
        "_template": "box",
        "_captcha": "false",
        "_replyto": order.customer_email,
        "name": order.customer_name,
        "email": order.customer_email,
        "message": order_email_body(order),
    }
    to = urllib.parse.quote(notify_email(), safe="")
    req = urllib.request.Request(
        f"{FORMSUBMIT_URL}{to}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "PrintMeMaybeShop/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read()
        if resp.status >= 400:
            raise RuntimeError(f"FormSubmit HTTP {resp.status}: {raw[:200]!r}")


def notify_new_order(order: Order) -> bool:
    """Email the studio. Never raises — checkout must still succeed."""
    if not mail_configured():
        logger.warning("Order #%s placed; email skipped (NOTIFY_EMAIL is empty).", order.id)
        return False
    try:
        if smtp_password():
            _send_via_smtp(build_order_email(order))
        else:
            _send_via_formsubmit(order)
    except Exception:
        logger.exception("Could not email order #%s", order.id)
        return False
    logger.info("Order #%s emailed to %s", order.id, notify_email())
    return True
