"""Product catalog and order persistence."""

from __future__ import annotations

from typing import Iterable

from src.db import get_connection
from src.models import CartLine, Product


def list_products(category: str | None = None) -> list[Product]:
    """Return all in-stock products, optionally filtered by category."""
    query = "SELECT * FROM products WHERE stock > 0"
    params: tuple[object, ...] = ()
    if category:
        query += " AND category = ?"
        params = (category,)
    query += " ORDER BY category, name"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [Product.from_row(row) for row in rows]


def list_categories() -> list[str]:
    """Distinct product categories for the shop filter bar."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT category FROM products ORDER BY category"
        ).fetchall()
    return [row["category"] for row in rows]


def get_product_by_slug(slug: str) -> Product | None:
    """Look up a single product for the detail page."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM products WHERE slug = ?", (slug,)).fetchone()
    return Product.from_row(row) if row else None


def get_products_by_ids(product_ids: Iterable[int]) -> dict[int, Product]:
    """Batch fetch products for cart rendering."""
    ids = list(product_ids)
    if not ids:
        return {}

    placeholders = ",".join("?" for _ in ids)
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM products WHERE id IN ({placeholders})",
            ids,
        ).fetchall()
    return {row["id"]: Product.from_row(row) for row in rows}


def build_cart_lines(cart: dict[str, int]) -> list[CartLine]:
    """Turn session cart {product_id: qty} into display lines."""
    if not cart:
        return []

    products = get_products_by_ids(int(pid) for pid in cart)
    lines: list[CartLine] = []
    for pid_str, qty in cart.items():
        product = products.get(int(pid_str))
        if product and qty > 0:
            lines.append(CartLine(product=product, quantity=min(qty, product.stock)))
    return lines


def cart_total_cents(lines: list[CartLine]) -> int:
    """Sum line totals for checkout."""
    return sum(line.line_total_cents for line in lines)


def place_order(
    *,
    customer_name: str,
    customer_email: str,
    shipping_address: str,
    lines: list[CartLine],
) -> int:
    """Persist an order and decrement stock atomically."""
    if not lines:
        raise ValueError("Cart is empty")

    total = cart_total_cents(lines)

    with get_connection() as conn:
        for line in lines:
            row = conn.execute(
                "SELECT stock FROM products WHERE id = ?",
                (line.product.id,),
            ).fetchone()
            if not row or row["stock"] < line.quantity:
                raise ValueError(f"Insufficient stock for {line.product.name}")

        cursor = conn.execute(
            """
            INSERT INTO orders (customer_name, customer_email, shipping_address, total_cents)
            VALUES (?, ?, ?, ?)
            """,
            (customer_name, customer_email, shipping_address, total),
        )
        order_id = cursor.lastrowid

        for line in lines:
            conn.execute(
                """
                INSERT INTO order_items (order_id, product_id, quantity, unit_price_cents)
                VALUES (?, ?, ?, ?)
                """,
                (order_id, line.product.id, line.quantity, line.product.price_cents),
            )
            conn.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ?",
                (line.quantity, line.product.id),
            )

    return int(order_id)
