"""Product catalog and order persistence."""

from __future__ import annotations

from typing import Iterable

from src.db import get_connection
from src.models import CartLine, Order, OrderItem, Product, order_total_cents


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
    """Sum line totals for checkout subtotal."""
    return sum(line.line_total_cents for line in lines)


def get_order(order_id: int) -> Order | None:
    """Fetch a placed order and its line items."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not row:
            return None
        return _order_from_row(conn, row)


def list_all_products() -> list[Product]:
    """Admin catalog including sold-out items."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM products ORDER BY category, name").fetchall()
    return [Product.from_row(row) for row in rows]


def set_product_stock(product_id: int, stock: int) -> None:
    """Set remaining stock from the admin stock page."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE products SET stock = ? WHERE id = ?",
            (max(0, stock), product_id),
        )


def list_orders(status: str | None = None) -> list[Order]:
    """Newest-first order list for the studio admin."""
    query = "SELECT * FROM orders"
    params: tuple[object, ...] = ()
    if status:
        query += " WHERE status = ?"
        params = (status,)
    query += " ORDER BY id DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [_order_from_row(conn, row) for row in rows]


def order_status_counts() -> dict[str, int]:
    """Counts for the admin status filter chips."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM orders GROUP BY status"
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    counts = {row["status"]: int(row["n"]) for row in rows}
    counts["all"] = int(total)
    return counts


def update_order_status(order_id: int, status: str) -> None:
    """Set status and restock when cancelling (or deduct again when reopening)."""
    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT status FROM orders WHERE id = ?", (order_id,)).fetchone()
        if not row:
            raise ValueError("Order not found")

        current = row["status"]
        if current == status:
            return

        items = conn.execute(
            "SELECT product_id, quantity FROM order_items WHERE order_id = ?",
            (order_id,),
        ).fetchall()

        if current != "cancelled" and status == "cancelled":
            for item in items:
                conn.execute(
                    "UPDATE products SET stock = stock + ? WHERE id = ?",
                    (item["quantity"], item["product_id"]),
                )
        elif current == "cancelled" and status != "cancelled":
            for item in items:
                product = conn.execute(
                    "SELECT name, stock FROM products WHERE id = ?",
                    (item["product_id"],),
                ).fetchone()
                if not product or product["stock"] < item["quantity"]:
                    name = product["name"] if product else "item"
                    raise ValueError(f"Insufficient stock to reopen for {name}")
            for item in items:
                conn.execute(
                    "UPDATE products SET stock = stock - ? WHERE id = ?",
                    (item["quantity"], item["product_id"]),
                )

        conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))


def update_order_notes(order_id: int, notes: str) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE orders SET notes = ? WHERE id = ?", (notes, order_id))


def _order_from_row(conn, row) -> Order:
    item_rows = conn.execute(
        """
        SELECT oi.quantity, oi.unit_price_cents, p.name AS product_name
        FROM order_items oi
        JOIN products p ON p.id = oi.product_id
        WHERE oi.order_id = ?
        ORDER BY oi.id
        """,
        (row["id"],),
    ).fetchall()
    items = [
        OrderItem(
            product_name=item["product_name"],
            quantity=item["quantity"],
            unit_price_cents=item["unit_price_cents"],
        )
        for item in item_rows
    ]
    keys = row.keys()
    return Order(
        id=row["id"],
        customer_name=row["customer_name"],
        customer_email=row["customer_email"],
        shipping_address=row["shipping_address"],
        total_cents=row["total_cents"],
        created_at=row["created_at"],
        items=items,
        status=row["status"] if "status" in keys else "new",
        notes=row["notes"] if "notes" in keys else "",
    )


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

    total = order_total_cents(cart_total_cents(lines))

    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        for line in lines:
            row = conn.execute(
                "SELECT stock FROM products WHERE id = ?",
                (line.product.id,),
            ).fetchone()
            if not row or row["stock"] < line.quantity:
                raise ValueError(f"Insufficient stock for {line.product.name}")

        cursor = conn.execute(
            """
            INSERT INTO orders (customer_name, customer_email, shipping_address, total_cents, status)
            VALUES (?, ?, ?, ?, 'new')
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
