"""Email the studio when a customer places an order."""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

from src.models import Order, format_money

logger = logging.getLogger(__name__)

DEFAULT_NOTIFY_EMAIL = "dimitrioupanagiotis@outlook.com"
DEFAULT_SMTP_HOST = "smtp-mail.outlook.com"
DEFAULT_SHOP_URL = "https://print-me-maybe.onrender.com"


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
    """True when we have a destination inbox and SMTP login."""
    return bool(notify_email() and smtp_user() and smtp_password())


def build_order_email(order: Order) -> EmailMessage:
    """Plain-text studio alert with Reply-To set to the customer."""
    shop = os.environ.get("SHOP_NAME", "Print Me Maybe")
    shipping = (
        "Free" if order.shipping_cents == 0 else format_money(order.shipping_cents)
    )
    lines = [
        f"New order #{order.id} — {shop}",
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
        ]
    )

    msg = EmailMessage()
    msg["Subject"] = f"New {shop} order #{order.id} ({order.total_display})"
    msg["From"] = smtp_user()
    msg["To"] = notify_email()
    msg["Reply-To"] = order.customer_email
    msg.set_content("\n".join(lines) + "\n")
    return msg


def _send_message(msg: EmailMessage) -> None:
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


def notify_new_order(order: Order) -> bool:
    """Email the studio. Never raises — checkout must still succeed."""
    if not mail_configured():
        logger.warning(
            "Order #%s placed; email skipped (set SMTP_PASSWORD on Render).",
            order.id,
        )
        return False
    try:
        _send_message(build_order_email(order))
    except Exception:
        logger.exception("Could not email order #%s", order.id)
        return False
    logger.info("Order #%s emailed to %s", order.id, notify_email())
    return True
