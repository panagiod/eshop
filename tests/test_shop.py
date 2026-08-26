"""Smoke tests for the Print Me Maybe shop."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.db import get_connection, init_schema
from src.main import app
from src.models import STANDARD_SHIPPING_CENTS, order_total_cents, shipping_cents
from src.seed import seed_products
from src.store import list_all_products


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
    assert "Made in Cyprus" in home.text
    assert "Floral Glasses Case" in home.text
    assert "€4.00" in home.text
    assert "Custom Cake Topper" in home.text
    assert "€15.00" in home.text
    assert "Teddy Bear Keychain" in home.text
    assert "€5.00" in home.text
    assert "/static/images/products/glasses-case.jpg" in home.text

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
    assert "Floral Glasses Case" in prints.text
    assert "Engraved Oak Coaster Set" not in prints.text

    laser = client.get("/?category=Laser Engraving")
    assert laser.status_code == 200
    assert "Engraved Oak Coaster Set" in laser.text
    assert "Floral Glasses Case" not in laser.text


def test_shipping_calculation() -> None:
    assert shipping_cents(400) == STANDARD_SHIPPING_CENTS
    assert shipping_cents(2500) == 0
    assert order_total_cents(400) == 400 + STANDARD_SHIPPING_CENTS


def test_add_to_cart_and_checkout_with_shipping() -> None:
    init_schema()
    seed_products()

    client = TestClient(app)
    products = client.get("/api/products").json()
    glasses = next(p for p in products if p["slug"] == "glasses-case")
    subtotal = glasses["price_cents"]
    shipping = shipping_cents(subtotal)
    total = order_total_cents(subtotal)

    add = client.post(
        "/cart/add",
        data={"product_id": glasses["id"], "quantity": 1},
        follow_redirects=False,
    )
    assert add.status_code == 303

    cart = client.get("/cart")
    assert cart.status_code == 200
    assert glasses["name"] in cart.text
    assert "Free shipping on orders over €25.00" in cart.text

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
    assert f"€{total / 100:.2f}" in checkout.text

    order_id = checkout.text.split("#")[1].split("<")[0]
    detail = client.get(f"/order/{order_id}")
    assert detail.status_code == 200
    assert glasses["name"] in detail.text
    assert f"€{shipping / 100:.2f}" in detail.text or "Free" in detail.text


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
    assert "Free shipping on orders over €25.00" not in cart.text


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
    assert glasses["name"] in stock_page.text

    client.post(f"/admin/stock/{glasses['id']}", data={"stock": "0"})
    hidden = client.get("/api/products").json()
    assert all(p["id"] != glasses["id"] for p in hidden)


def test_cancel_restocks_and_reopen_deducts() -> None:
    init_schema()
    seed_products()

    client = TestClient(app)
    products = client.get("/api/products").json()
    glasses = next(p for p in products if p["slug"] == "glasses-case")
    before = next(p for p in list_all_products() if p.slug == "glasses-case").stock

    client.post("/cart/add", data={"product_id": glasses["id"], "quantity": 1})
    checkout = client.post(
        "/checkout",
        data={
            "customer_name": "Cancel Case",
            "customer_email": "cancel@example.com",
            "shipping_address": "9 Restock Rd",
        },
    )
    order_id = checkout.text.split("#")[1].split("<")[0]
    after_order = next(p for p in list_all_products() if p.slug == "glasses-case").stock
    assert after_order == before - 1

    client.post("/admin/login", data={"password": "printmemaybe"})
    client.post(
        f"/admin/orders/{order_id}",
        data={"status": "cancelled", "notes": ""},
    )
    after_cancel = next(p for p in list_all_products() if p.slug == "glasses-case").stock
    assert after_cancel == before

    client.post(
        f"/admin/orders/{order_id}",
        data={"status": "in_progress", "notes": ""},
    )
    after_reopen = next(p for p in list_all_products() if p.slug == "glasses-case").stock
    assert after_reopen == before - 1


def test_seed_updates_prices_without_resetting_stock() -> None:
    init_schema()
    seed_products()
    with get_connection() as conn:
        conn.execute(
            "UPDATE products SET price_cents = 1, stock = 7 WHERE slug = 'custom-cake-topper'"
        )
    seed_products()
    product = next(p for p in list_all_products() if p.slug == "custom-cake-topper")
    assert product.price_cents == 1500
    assert product.stock == 7
