"""Smoke tests for the Print Me Maybe shop."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.db import init_schema
from src.main import app
from src.models import STANDARD_SHIPPING_CENTS, order_total_cents, shipping_cents
from src.seed import seed_products


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))


def test_health_and_catalog() -> None:
    init_schema()
    seed_products()

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    home = client.get("/")
    assert home.status_code == 200
    assert "Print Me Maybe" in home.text
    assert "LaserCraft 27" in home.text
    assert "print.me.maybe" in home.text
    assert "lasercraft.27" in home.text

    api = client.get("/api/products")
    assert api.status_code == 200
    products = api.json()
    assert len(products) >= 1
    categories = {p["category"] for p in products}
    assert "3D Prints" in categories
    assert "Laser Engraving" in categories


def test_category_filter() -> None:
    init_schema()
    seed_products()

    client = TestClient(app)
    prints = client.get("/?category=3D Prints")
    assert prints.status_code == 200
    assert "Spherical Apple Watch Dock" in prints.text
    assert "Engraved Oak Coaster Set" not in prints.text

    laser = client.get("/?category=Laser Engraving")
    assert laser.status_code == 200
    assert "Engraved Oak Coaster Set" in laser.text
    assert "Spherical Apple Watch Dock" not in laser.text


def test_shipping_calculation() -> None:
    assert shipping_cents(2499) == STANDARD_SHIPPING_CENTS
    assert shipping_cents(7500) == 0
    assert order_total_cents(2499) == 2499 + STANDARD_SHIPPING_CENTS


def test_add_to_cart_and_checkout_with_shipping() -> None:
    init_schema()
    seed_products()

    client = TestClient(app)
    products = client.get("/api/products").json()
    nozzle = next(p for p in products if p["slug"] == "nozzle-case-a1")
    subtotal = nozzle["price_cents"]
    shipping = shipping_cents(subtotal)
    total = order_total_cents(subtotal)

    add = client.post(
        "/cart/add",
        data={"product_id": nozzle["id"], "quantity": 1},
        follow_redirects=False,
    )
    assert add.status_code == 303

    cart = client.get("/cart")
    assert cart.status_code == 200
    assert nozzle["name"] in cart.text
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
    assert nozzle["name"] in detail.text
    assert f"${shipping / 100:.2f}" in detail.text or "Free" in detail.text


def test_free_shipping_on_large_order() -> None:
    init_schema()
    seed_products()

    client = TestClient(app)
    products = client.get("/api/products").json()
    sign = next(p for p in products if p["slug"] == "family-name-sign")

    client.post("/cart/add", data={"product_id": sign["id"], "quantity": 1})

    cart = client.get("/cart")
    assert cart.status_code == 200
    assert "Free" in cart.text
    assert "Free shipping on orders over $75" not in cart.text


def test_admin_requires_login() -> None:
    init_schema()
    seed_products()

    client = TestClient(app)
    listing = client.get("/admin/orders", follow_redirects=False)
    assert listing.status_code == 303
    assert listing.headers["location"] == "/admin/login"


def test_admin_orders_and_stock() -> None:
    init_schema()
    seed_products()

    client = TestClient(app)
    products = client.get("/api/products").json()
    nozzle = next(p for p in products if p["slug"] == "nozzle-case-a1")
    client.post("/cart/add", data={"product_id": nozzle["id"], "quantity": 1})
    checkout = client.post(
        "/checkout",
        data={
            "customer_name": "Ada Lovelace",
            "customer_email": "ada@example.com",
            "shipping_address": "12 Engine St",
        },
    )
    assert "Thank you" in checkout.text
    order_id = checkout.text.split("#")[1].split("<")[0]

    denied = client.post("/admin/login", data={"password": "wrong"}, follow_redirects=False)
    assert denied.status_code == 401

    login = client.post("/admin/login", data={"password": "printmemaybe"}, follow_redirects=False)
    assert login.status_code == 303

    orders = client.get("/admin/orders")
    assert orders.status_code == 200
    assert "Ada Lovelace" in orders.text
    assert f">{order_id}<" in orders.text or f"/admin/orders/{order_id}" in orders.text

    save = client.post(
        f"/admin/orders/{order_id}",
        data={"status": "in_progress", "notes": "DM received for custom name"},
        follow_redirects=False,
    )
    assert save.status_code == 303

    detail = client.get(f"/admin/orders/{order_id}")
    assert detail.status_code == 200
    assert "In progress" in detail.text
    assert "DM received for custom name" in detail.text

    stock_page = client.get("/admin/stock")
    assert stock_page.status_code == 200
    assert nozzle["name"] in stock_page.text

    client.post(f"/admin/stock/{nozzle['id']}", data={"stock": "0"})
    hidden = client.get("/api/products").json()
    assert all(p["id"] != nozzle["id"] for p in hidden)
