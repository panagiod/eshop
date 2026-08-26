"""Smoke tests for the Harbor e-shop."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.db import init_schema
from src.main import app
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


def test_add_to_cart_and_checkout() -> None:
    init_schema()
    seed_products()

    client = TestClient(app)
    products = client.get("/api/products").json()
    product_id = products[0]["id"]

    add = client.post("/cart/add", data={"product_id": product_id, "quantity": 1}, follow_redirects=False)
    assert add.status_code == 303

    cart = client.get("/cart")
    assert cart.status_code == 200
    assert products[0]["name"] in cart.text

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
