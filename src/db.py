"""SQLite database helpers — file-backed store for products and orders."""

from __future__ import annotations

import os
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

# Default path works locally; production sets DATA_DIR to a real disk (Hetzner: /var/lib/eshop).
def data_dir() -> Path:
    return Path(os.environ.get("DATA_DIR", "/tmp/eshop-data"))


def data_persistent() -> bool:
    """False when SQLite lives under /tmp (wiped on reboot / Render Free)."""
    return not str(data_dir()).startswith("/tmp")


def db_path() -> Path:
    return data_dir() / "eshop.db"


def ensure_data_dir() -> None:
    """Create the data directory before opening SQLite (containers use read-only root)."""
    data_dir().mkdir(parents=True, exist_ok=True)


def product_images_dir() -> Path:
    """Writable folder for photos uploaded from the admin stock page."""
    path = data_dir() / "product-images"
    path.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Yield a connection with row dict access and foreign keys enabled."""
    ensure_data_dir()
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_schema() -> None:
    """Create tables if this is a fresh database."""
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                price_cents INTEGER NOT NULL,
                image_url TEXT NOT NULL,
                category TEXT NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                shipping_address TEXT NOT NULL,
                total_cents INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'new',
                notes TEXT NOT NULL DEFAULT '',
                lookup_token TEXT UNIQUE,
                payment_status TEXT NOT NULL DEFAULT 'unpaid',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                product_id INTEGER NOT NULL REFERENCES products(id),
                quantity INTEGER NOT NULL,
                unit_price_cents INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS stripe_sessions (
                session_id TEXT PRIMARY KEY,
                order_id INTEGER NOT NULL REFERENCES orders(id),
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )
        columns = {row[1] for row in conn.execute("PRAGMA table_info(orders)").fetchall()}
        if "status" not in columns:
            conn.execute("ALTER TABLE orders ADD COLUMN status TEXT NOT NULL DEFAULT 'new'")
        if "notes" not in columns:
            conn.execute("ALTER TABLE orders ADD COLUMN notes TEXT NOT NULL DEFAULT ''")
        if "lookup_token" not in columns:
            conn.execute("ALTER TABLE orders ADD COLUMN lookup_token TEXT")
        if "payment_status" not in columns:
            conn.execute(
                "ALTER TABLE orders ADD COLUMN payment_status TEXT NOT NULL DEFAULT 'unpaid'"
            )
        missing = conn.execute(
            "SELECT id FROM orders WHERE lookup_token IS NULL OR lookup_token = ''"
        ).fetchall()
        if missing:
            for row in missing:
                conn.execute(
                    "UPDATE orders SET lookup_token = ? WHERE id = ?",
                    (secrets.token_urlsafe(16), row["id"]),
                )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_lookup_token ON orders(lookup_token)"
        )
