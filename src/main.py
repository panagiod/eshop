"""FastAPI storefront — catalog, cart, and checkout."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from src.admin import router as admin_router
from src.db import data_is_persistent, init_schema, product_images_dir, warn_if_ephemeral_production
from src.models import FREE_SHIPPING_THRESHOLD_CENTS, format_money, order_total_cents, shipping_cents
from src.ratelimit import RateLimitMiddleware
from src.security import SecurityHeadersMiddleware, require_production_secrets, session_https_only, session_secret
from src.seed import seed_products
from src.notify import mail_configured, schedule_order_email
from src.store import (
    build_cart_lines,
    cart_total_cents,
    get_order,
    get_order_by_token,
    get_product,
    get_product_by_slug,
    list_categories,
    list_products,
    place_order,
)

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = session_secret()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Prepare database and demo catalog on container boot."""
    require_production_secrets()
    warn_if_ephemeral_production()
    init_schema()
    seed_products()
    yield


app = FastAPI(title="Print Me Maybe", version="0.2.0", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=60 * 60 * 24 * 7, same_site="lax", https_only=session_https_only())
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals["format_money"] = format_money
templates.env.globals["free_shipping_threshold"] = format_money(FREE_SHIPPING_THRESHOLD_CENTS)
app.include_router(admin_router)


def get_cart(request: Request) -> dict[str, int]:
    """Session cart maps product id strings to quantities."""
    raw = request.session.get("cart", {})
    if not isinstance(raw, dict):
        return {}
    return {str(k): int(v) for k, v in raw.items() if int(v) > 0}


def save_cart(request: Request, cart: dict[str, int]) -> None:
    request.session["cart"] = {k: v for k, v in cart.items() if v > 0}


def cart_count(cart: dict[str, int]) -> int:
    return sum(cart.values())


def shop_name() -> str:
    return os.environ.get("SHOP_NAME", "Print Me Maybe")


def checkout_totals(lines: list) -> dict[str, int]:
    """Shared subtotal, shipping, and total for cart and checkout views."""
    subtotal = cart_total_cents(lines)
    shipping = shipping_cents(subtotal)
    return {
        "subtotal_cents": subtotal,
        "shipping_cents": shipping,
        "total_cents": order_total_cents(subtotal),
    }


@app.get("/health")
def health() -> dict[str, str | bool]:
    """Liveness plus whether THIS process can send mail (no secrets)."""
    return {"status": "ok", "service": "eshop", "mail": mail_configured(), "persistent": data_is_persistent()}


@app.get("/media/products/{filename}")
def serve_product_image(filename: str) -> FileResponse:
    """Serve a photo uploaded from the studio admin (stored under DATA_DIR)."""
    safe = Path(filename).name
    if not safe or safe != filename:
        raise HTTPException(status_code=404, detail="Not found")
    path = (product_images_dir() / safe).resolve()
    root = product_images_dir().resolve()
    if not path.is_file() or path.parent != root:
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(
        path,
        media_type=_image_media_type(safe),
        headers={"X-Content-Type-Options": "nosniff", "Content-Disposition": "inline"},
    )


def _image_media_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(ext, "application/octet-stream")


@app.get("/", response_class=HTMLResponse)
def home(request: Request, category: str | None = None) -> Any:
    cart = get_cart(request)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "products": list_products(category),
            "categories": list_categories(),
            "active_category": category,
            "cart_count": cart_count(cart),
            "shop_name": shop_name(),
        },
    )


@app.get("/product/{slug}", response_class=HTMLResponse)
def product_detail(request: Request, slug: str) -> Any:
    product = get_product_by_slug(slug)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    cart = get_cart(request)
    return templates.TemplateResponse(
        request,
        "product.html",
        {
            "product": product,
            "cart_count": cart_count(cart),
            "shop_name": shop_name(),
        },
    )


@app.post("/cart/add")
def cart_add(request: Request, product_id: int = Form(...), quantity: int = Form(1)) -> RedirectResponse:
    product = get_product(product_id)
    if not product or product.stock <= 0:
        return RedirectResponse(url="/", status_code=303)
    cart = get_cart(request)
    key = str(product_id)
    wanted = cart.get(key, 0) + max(1, min(quantity, 99))
    cart[key] = min(wanted, product.stock)
    save_cart(request, cart)
    return RedirectResponse(url="/cart", status_code=303)


@app.post("/cart/update")
def cart_update(request: Request, product_id: int = Form(...), quantity: int = Form(...)) -> RedirectResponse:
    cart = get_cart(request)
    key = str(product_id)
    if quantity <= 0:
        cart.pop(key, None)
    else:
        product = get_product(product_id)
        if not product or product.stock <= 0:
            cart.pop(key, None)
        else:
            cart[key] = min(max(quantity, 0), product.stock)
    save_cart(request, cart)
    return RedirectResponse(url="/cart", status_code=303)


@app.get("/cart", response_class=HTMLResponse)
def cart_page(request: Request) -> Any:
    cart = get_cart(request)
    lines = build_cart_lines(cart)
    totals = checkout_totals(lines)
    return templates.TemplateResponse(
        request,
        "cart.html",
        {
            "lines": lines,
            "cart_count": cart_count(cart),
            "shop_name": shop_name(),
            **totals,
        },
    )


@app.get("/checkout", response_class=HTMLResponse)
def checkout_page(request: Request) -> Any:
    cart = get_cart(request)
    lines = build_cart_lines(cart)
    if not lines:
        return RedirectResponse(url="/cart", status_code=303)

    totals = checkout_totals(lines)
    return templates.TemplateResponse(
        request,
        "checkout.html",
        {
            "lines": lines,
            "cart_count": cart_count(cart),
            "shop_name": shop_name(),
            **totals,
        },
    )


@app.post("/checkout", response_class=HTMLResponse)
def checkout_submit(
    request: Request,
    customer_name: str = Form(...),
    customer_email: str = Form(...),
    shipping_address: str = Form(...),
) -> Any:
    cart = get_cart(request)
    lines = build_cart_lines(cart)
    if not lines:
        return RedirectResponse(url="/cart", status_code=303)

    totals = checkout_totals(lines)

    try:
        order_id = place_order(
            customer_name=customer_name.strip(),
            customer_email=customer_email.strip(),
            shipping_address=shipping_address.strip(),
            lines=lines,
        )
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "checkout.html",
            {
                "lines": lines,
                "cart_count": cart_count(cart),
                "shop_name": shop_name(),
                "error": str(exc),
                **totals,
            },
            status_code=400,
        )

    save_cart(request, {})
    order = get_order(order_id)
    if order:
        schedule_order_email(order)
    return templates.TemplateResponse(
        request,
        "order_complete.html",
        {
            "order_id": order_id,
            "lookup_token": order.lookup_token if order else "",
            "cart_count": 0,
            "shop_name": shop_name(),
            **totals,
        },
    )


@app.get("/order/{token}", response_class=HTMLResponse)
def order_detail(request: Request, token: str) -> Any:
    order = get_order_by_token(token)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return templates.TemplateResponse(
        request,
        "order_detail.html",
        {
            "order": order,
            "cart_count": cart_count(get_cart(request)),
            "shop_name": shop_name(),
            "is_admin": False,
        },
    )


@app.get("/api/products")
def api_products() -> JSONResponse:
    """Lightweight JSON catalog for integrations or future SPA."""
    products = list_products()
    payload = [
        {
            "id": p.id,
            "slug": p.slug,
            "name": p.name,
            "price_cents": p.price_cents,
            "category": p.category,
            "image_url": p.image_url,
        }
        for p in products
    ]
    return JSONResponse(payload)
