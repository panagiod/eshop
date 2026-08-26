"""Email the studio for new orders and blocked attack-shaped traffic."""

from __future__ import annotations

import json
import logging
import os
import smtplib
import ssl
import time
import urllib.parse
import urllib.request
from email.message import EmailMessage
from threading import Lock

from src.models import Order, format_money

logger = logging.getLogger(__name__)

DEFAULT_NOTIFY_EMAIL = "dimitrioupanagiotis@outlook.com"
DEFAULT_SMTP_HOST = "smtp-mail.outlook.com"
DEFAULT_SHOP_URL = "https://print-me-maybe.onrender.com"
FORMSUBMIT_URL = "https://formsubmit.co/ajax/"

_alert_last: dict[str, float] = {}
_alert_lock = Lock()
_failed_logins: dict[str, list[float]] = {}


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


def shop_name() -> str:
    return os.environ.get("SHOP_NAME", "Print Me Maybe")


def mail_configured() -> bool:
    """True when we have an inbox. No mail password is required."""
    return bool(notify_email())


def reset_alerts() -> None:
    """Clear attack-alert cooldowns (tests)."""
    with _alert_lock:
        _alert_last.clear()
        _failed_logins.clear()


def _alert_cooldown() -> int:
    raw = os.environ.get("ATTACK_ALERT_COOLDOWN", "3600").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 3600


def _alert_allowed(kind: str) -> bool:
    now = time.monotonic()
    with _alert_lock:
        last = _alert_last.get(kind, 0)
        if now - last < _alert_cooldown():
            return False
        _alert_last[kind] = now
        return True


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


def build_customer_email(order: Order) -> EmailMessage:
    """Confirmation to the buyer with the unguessable order link."""
    link = (
        f"{shop_url()}/order/{order.lookup_token}"
        if order.lookup_token
        else shop_url()
    )
    lines = [
        f"Thank you for your {shop_name()} order #{order.id}.",
        "",
        f"Total: {order.total_display}",
        "",
        "View your order:",
        link,
        "",
        "No payment was collected at checkout. For custom names, photos, or files, reply or DM Instagram.",
        "",
    ]
    msg = EmailMessage()
    msg["Subject"] = f"{shop_name()} order #{order.id}"
    msg["From"] = smtp_user()
    msg["To"] = order.customer_email
    msg.set_content("\n".join(lines))
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


def _send_via_formsubmit(*, subject: str, body: str, reply_to: str = "", name: str = "") -> None:
    payload = {
        "_subject": subject,
        "_template": "box",
        "_captcha": "false",
        "name": name or shop_name(),
        "message": body,
    }
    if reply_to:
        payload["_replyto"] = reply_to
        payload["email"] = reply_to
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


def _deliver_studio(*, subject: str, body: str, reply_to: str = "", name: str = "") -> None:
    if smtp_password():
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = smtp_user()
        msg["To"] = notify_email()
        if reply_to:
            msg["Reply-To"] = reply_to
        msg.set_content(body)
        _send_via_smtp(msg)
        return
    _send_via_formsubmit(subject=subject, body=body, reply_to=reply_to, name=name)


def notify_new_order(order: Order) -> bool:
    """Email the studio. Never raises — checkout must still succeed."""
    if not mail_configured():
        logger.warning("Order #%s placed; email skipped (NOTIFY_EMAIL is empty).", order.id)
        return False
    try:
        _deliver_studio(
            subject=order_email_subject(order),
            body=order_email_body(order),
            reply_to=order.customer_email,
            name=order.customer_name,
        )
    except Exception:
        logger.exception("Could not email order #%s", order.id)
        return False
    if smtp_password():
        try:
            _send_via_smtp(build_customer_email(order))
        except Exception:
            logger.exception("Could not email customer for order #%s", order.id)
    logger.info("Order #%s emailed to %s", order.id, notify_email())
    return True


def _attack_copy(kind: str, ip: str) -> tuple[str, str]:
    if kind == "login":
        subject = f"{shop_name()}: blocked studio login attempts"
        body = (
            f"The shop blocked repeated studio login tries from {ip}.\n\n"
            "The visitor is locked out for a few minutes. You do not need to do anything "
            "unless you were logging in from that network — if so, wait and try again.\n\n"
            f"Studio login: {shop_url()}/admin/login\n"
        )
    else:
        subject = f"{shop_name()}: blocked checkout flood"
        body = (
            f"The shop blocked repeated checkout attempts from {ip}.\n\n"
            "No extra orders were created. You do not need to do anything.\n\n"
            f"Studio orders: {shop_url()}/admin/orders\n"
        )
    return subject, body


def notify_attack(kind: str, ip: str) -> bool:
    """Email the studio after blocked login or checkout. At most once per cooldown."""
    if kind not in {"login", "checkout"}:
        return False
    if not mail_configured():
        return False
    if not _alert_allowed(kind):
        return False
    subject, body = _attack_copy(kind, ip or "unknown")
    try:
        _deliver_studio(subject=subject, body=body, name="Shop security")
    except Exception:
        logger.exception("Could not send attack alert (%s)", kind)
        with _alert_lock:
            _alert_last.pop(kind, None)
        return False
    logger.warning("Attack alert emailed (%s) from %s", kind, ip)
    return True


def record_failed_login(ip: str) -> bool:
    """Alert after several failed studio logins from the same visitor."""
    now = time.monotonic()
    window = 900
    threshold = 3
    key = ip or "unknown"
    with _alert_lock:
        stamps = [t for t in _failed_logins.get(key, []) if now - t < window]
        stamps.append(now)
        _failed_logins[key] = stamps
        should_alert = len(stamps) >= threshold
    if should_alert:
        return notify_attack("login", key)
    return False
