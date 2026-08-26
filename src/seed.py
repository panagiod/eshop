"""Seed catalog data on first boot — safe to re-run (skips when products exist)."""

from __future__ import annotations

from src.db import get_connection

# Starter catalog: enough variety for a demo storefront without external images.
CATALOG = [
    {
        "slug": "wireless-headphones",
        "name": "Aurora Wireless Headphones",
        "description": "Noise-cancelling over-ear headphones with 30-hour battery life.",
        "price_cents": 8999,
        "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&h=600&fit=crop",
        "category": "Audio",
        "stock": 42,
    },
    {
        "slug": "smart-watch",
        "name": "Pulse Smart Watch",
        "description": "Fitness tracking, heart-rate monitor, and 5-day battery in a slim case.",
        "price_cents": 14999,
        "image_url": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&h=600&fit=crop",
        "category": "Wearables",
        "stock": 28,
    },
    {
        "slug": "canvas-tote",
        "name": "Harbor Canvas Tote",
        "description": "Reinforced cotton tote with interior pocket — perfect for daily carry.",
        "price_cents": 2499,
        "image_url": "https://images.unsplash.com/photo-1590874103328-eac38a683ce7?w=600&h=600&fit=crop",
        "category": "Bags",
        "stock": 65,
    },
    {
        "slug": "ceramic-mug",
        "name": "Morning Ritual Mug",
        "description": "350 ml double-wall ceramic mug that keeps coffee hot longer.",
        "price_cents": 1899,
        "image_url": "https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?w=600&h=600&fit=crop",
        "category": "Home",
        "stock": 120,
    },
    {
        "slug": "running-shoes",
        "name": "Trail Runner Pro",
        "description": "Lightweight mesh upper with responsive foam for road and light trail.",
        "price_cents": 11999,
        "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&h=600&fit=crop",
        "category": "Footwear",
        "stock": 35,
    },
    {
        "slug": "desk-lamp",
        "name": "Lumen Desk Lamp",
        "description": "Adjustable LED lamp with warm/cool modes and USB charging port.",
        "price_cents": 4599,
        "image_url": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=600&h=600&fit=crop",
        "category": "Home",
        "stock": 50,
    },
    {
        "slug": "backpack",
        "name": "Urban Commuter Backpack",
        "description": "Water-resistant 20 L pack with padded laptop sleeve up to 16 inches.",
        "price_cents": 7999,
        "image_url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=600&h=600&fit=crop",
        "category": "Bags",
        "stock": 40,
    },
    {
        "slug": "sunglasses",
        "name": "Coast Polarized Sunglasses",
        "description": "UV400 polarized lenses in a lightweight acetate frame.",
        "price_cents": 5999,
        "image_url": "https://images.unsplash.com/photo-1572635196237-14b3f281503f?w=600&h=600&fit=crop",
        "category": "Accessories",
        "stock": 55,
    },
    {
        "slug": "yoga-mat",
        "name": "Flow Yoga Mat",
        "description": "5 mm natural rubber mat with alignment guides and carrying strap.",
        "price_cents": 3499,
        "image_url": "https://images.unsplash.com/photo-1601925260368-ae2f83cf8b7f?w=600&h=600&fit=crop",
        "category": "Fitness",
        "stock": 70,
    },
    {
        "slug": "bluetooth-speaker",
        "name": "Ripple Mini Speaker",
        "description": "Pocket-sized speaker with 360° sound and IPX7 water resistance.",
        "price_cents": 4999,
        "image_url": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=600&h=600&fit=crop",
        "category": "Audio",
        "stock": 80,
    },
    {
        "slug": "notebook-set",
        "name": "Studio Notebook Set",
        "description": "Three A5 dotted notebooks with lay-flat binding and thick paper.",
        "price_cents": 2199,
        "image_url": "https://images.unsplash.com/photo-1531346878377-a5be20888e57?w=600&h=600&fit=crop",
        "category": "Stationery",
        "stock": 90,
    },
    {
        "slug": "plant-pot",
        "name": "Terracotta Planter",
        "description": "Hand-glazed ceramic pot with drainage tray — 18 cm diameter.",
        "price_cents": 2799,
        "image_url": "https://images.unsplash.com/photo-1485955900006-10f4d324d411?w=600&h=600&fit=crop",
        "category": "Home",
        "stock": 45,
    },
]


def seed_products() -> None:
    """Insert demo products when the catalog table is empty."""
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count > 0:
            return

        conn.executemany(
            """
            INSERT INTO products (slug, name, description, price_cents, image_url, category, stock)
            VALUES (:slug, :name, :description, :price_cents, :image_url, :category, :stock)
            """,
            CATALOG,
        )
