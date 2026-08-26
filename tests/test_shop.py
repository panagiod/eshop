"""Smoke tests for the Harbor e-shop."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.db import init_schema
from src.main import app
from src.models import STANDARD_SHIPPING_CENTS, order_total_cents, shipping_cents
from src.seed import seed_products


def test_health_and_catalog() -> None:
    init_schema()
    seed_products()

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    home = client.get("/")
    assert home.status_code == 200
    assert "Harbor" in home.text

    api = client.get("/api/products")
    assert api.status_code == 200
    products = api.json()
    assert len(products) >= 1


def test_category_filter() -> None:
    init_schema()
    seed_products()

    client = TestClient(app)
    audio = client.get("/?category=Audio")
    assert audio.status_code == 200
    assert "Aurora Wireless Headphones" in audio.text

    bags = client.get("/?category=Bags")
    assert bags.status_code == 200
    assert "Harbor Canvas Tote" in bags.text
    assert "Aurora Wireless Headphones" not in bags.text


def test_shipping_calculation() -> None:
    assert shipping_cents(2499) == STANDARD_SHIPPING_CENTS
    assert shipping_cents(7500) == 0
    assert order_total_cents(2499) == 2499 + STANDARD_SHIPPING_CENTS


def test_add_to_cart_and_checkout_with_shipping() -> None:
    init_schema()
    seed_products()

    client = TestClient(app)
    products = client.get("/api/products").json()
    tote = next(p for p in products if p["slug"] == "canvas-tote")
    subtotal = tote["price_cents"]
    shipping = shipping_cents(subtotal)
    total = order_total_cents(subtotal)

    add = client.post(
        "/cart/add",
        data={"product_id": tote["id"], "quantity": 1},
        follow_redirects=False,
    )
    assert add.status_code == 303

    cart = client.get("/cart")
    assert cart.status_code == 200
    assert tote["name"] in cart.text
    assert "Free shipping on orders over $75" in cart.text

    checkout = client.post(
        "/checkout",
        data={
            "customer_name": "Test User",
            "customer_email": "test@example.com",
            "shipping_address": "123 Test St",
        },
    )
    assert checkout.status_code == 200
    assert "Thank you" in checkout.text
    assert f"${total / 100:.2f}" in checkout.text

    order_id = checkout.text.split("#")[1].split("<")[0]
    detail = client.get(f"/order/{order_id}")
    assert detail.status_code == 200
    assert tote["name"] in detail.text
    assert f"${shipping / 100:.2f}" in detail.text or "Free" in detail.text


def test_free_shipping_on_large_order() -> None:
    init_schema()
    seed_products()

    client = TestClient(app)
    products = client.get("/api/products").json()
    headphones = next(p for p in products if p["slug"] == "wireless-headphones")

    client.post("/cart/add", data={"product_id": headphones["id"], "quantity": 1})

    cart = client.get("/cart")
    assert cart.status_code == 200
    assert "Free" in cart.text
    assert "Free shipping on orders over $75" not in cart.text
