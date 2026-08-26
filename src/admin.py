"""Password-protected studio admin: orders and stock."""

from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from src.models import (
    FREE_SHIPPING_THRESHOLD_CENTS,
    ORDER_STATUS_LABELS,
    ORDER_STATUSES,
    format_money,
)
from src.store import (
    get_order,
    list_all_products,
    list_orders,
    order_status_counts,
    set_product_stock,
    update_order_notes,
    update_order_status,
)

BASE_DIR = Path(__file__).resolve().parent.parent
router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals["format_money"] = format_money
templates.env.globals["free_shipping_threshold"] = format_money(FREE_SHIPPING_THRESHOLD_CENTS)


def shop_name() -> str:
    return os.environ.get("SHOP_NAME", "Print Me Maybe")


def admin_password() -> str:
    return os.environ.get("ADMIN_PASSWORD", "printmemaybe")


def is_admin(request: Request) -> bool:
    return bool(request.session.get("is_admin"))


def require_admin(request: Request) -> RedirectResponse | None:
    if is_admin(request):
        return None
    return RedirectResponse(url="/admin/login", status_code=303)


def _ctx(request: Request, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    data = {
        "shop_name": shop_name(),
        "cart_count": 0,
        "is_admin": True,
        "status_labels": ORDER_STATUS_LABELS,
        "statuses": ORDER_STATUSES,
    }
    if extra:
        data.update(extra)
    return data


@router.get("/login")
def login_page(request: Request) -> Any:
    if is_admin(request):
        return RedirectResponse(url="/admin/orders", status_code=303)
    return templates.TemplateResponse(
        request,
        "admin_login.html",
        {"shop_name": shop_name(), "cart_count": 0, "is_admin": False, "error": None},
    )


@router.post("/login")
def login_submit(request: Request, password: str = Form(...)) -> Any:
    expected = admin_password()
    given_digest = hashlib.sha256(password.encode("utf-8")).digest()
    expected_digest = hashlib.sha256(expected.encode("utf-8")).digest()
    if expected and hmac.compare_digest(given_digest, expected_digest):
        request.session["is_admin"] = True
        return RedirectResponse(url="/admin/orders", status_code=303)
    return templates.TemplateResponse(
        request,
        "admin_login.html",
        {
            "shop_name": shop_name(),
            "cart_count": 0,
            "is_admin": False,
            "error": "Wrong password.",
        },
        status_code=401,
    )


@router.post("/logout")
def logout(request: Request) -> RedirectResponse:
    request.session.pop("is_admin", None)
    return RedirectResponse(url="/admin/login", status_code=303)


@router.get("")
def admin_home(request: Request) -> RedirectResponse:
    gate = require_admin(request)
    if gate:
        return gate
    return RedirectResponse(url="/admin/orders", status_code=303)


@router.get("/orders")
def orders_page(request: Request, status: str | None = None) -> Any:
    gate = require_admin(request)
    if gate:
        return gate
    if status and status not in ORDER_STATUSES:
        status = None
    return templates.TemplateResponse(
        request,
        "admin_orders.html",
        _ctx(
            request,
            {
                "orders": list_orders(status),
                "counts": order_status_counts(),
                "active_status": status,
            },
        ),
    )


@router.get("/orders/{order_id}")
def order_page(request: Request, order_id: int) -> Any:
    gate = require_admin(request)
    if gate:
        return gate
    order = get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return templates.TemplateResponse(
        request,
        "admin_order.html",
        _ctx(request, {"order": order}),
    )


@router.post("/orders/{order_id}")
def order_update(
    request: Request,
    order_id: int,
    status: str = Form(...),
    notes: str = Form(""),
) -> RedirectResponse:
    gate = require_admin(request)
    if gate:
        return gate
    if status not in ORDER_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    if not get_order(order_id):
        raise HTTPException(status_code=404, detail="Order not found")
    try:
        update_order_status(order_id, status)
    except ValueError as exc:
        order = get_order(order_id)
        return templates.TemplateResponse(
            request,
            "admin_order.html",
            _ctx(request, {"order": order, "error": str(exc)}),
            status_code=400,
        )
    update_order_notes(order_id, notes.strip())
    return RedirectResponse(url=f"/admin/orders/{order_id}", status_code=303)


@router.get("/stock")
def stock_page(request: Request) -> Any:
    gate = require_admin(request)
    if gate:
        return gate
    return templates.TemplateResponse(
        request,
        "admin_stock.html",
        _ctx(request, {"products": list_all_products()}),
    )


@router.post("/stock/{product_id}")
def stock_update(
    request: Request,
    product_id: int,
    stock: int = Form(...),
) -> RedirectResponse:
    gate = require_admin(request)
    if gate:
        return gate
    set_product_stock(product_id, stock)
    return RedirectResponse(url="/admin/stock", status_code=303)
