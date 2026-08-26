"""Seed catalog — Print Me Maybe (3D) and LaserCraft 27 (laser engraving)."""

from __future__ import annotations

from src.db import get_connection

# Real-world product mix inspired by @print.me.maybe (MakerWorld/Printables)
# and @lasercraft.27 custom engraving work.
CATALOG = [
    {
        "slug": "mini-bookshelf-books",
        "name": "Mini Anxiety Bookshelf Set",
        "description": "Tiny 3D-printed books for a desktop anxiety bookshelf — a Print Me Maybe everyday design.",
        "price_cents": 1899,
        "image_url": "https://images.unsplash.com/photo-1512820538081-55d60e3bbd90?w=600&h=600&fit=crop",
        "category": "3D Prints",
        "stock": 40,
    },
    {
        "slug": "apple-watch-dock",
        "name": "Spherical Apple Watch Dock",
        "description": "Print-in-place spherical stand that cradles your watch overnight. Compact desk piece from Print Me Maybe.",
        "price_cents": 2499,
        "image_url": "https://images.unsplash.com/photo-1434493789847-2f02dc6ca35d?w=600&h=600&fit=crop",
        "category": "3D Prints",
        "stock": 32,
    },
    {
        "slug": "nozzle-case-a1",
        "name": "Bambu A1 Nozzle Case",
        "description": "Organizer case for Bambu Lab A1 / A1 mini nozzles. Fits in a tool drawer; printed in durable PETG.",
        "price_cents": 1299,
        "image_url": "https://images.unsplash.com/photo-1631897642056-87c81992046b?w=600&h=600&fit=crop",
        "category": "3D Prints",
        "stock": 55,
    },
    {
        "slug": "laptop-stand",
        "name": "Simple Laptop Riser",
        "description": "Minimal two-piece riser that lifts a laptop for a better desk angle. No fasteners — snap together and print.",
        "price_cents": 2999,
        "image_url": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=600&h=600&fit=crop",
        "category": "3D Prints",
        "stock": 28,
    },
    {
        "slug": "tablet-stand",
        "name": "Tilted Tablet Stand",
        "description": "Angled stand for iPad and similar tablets. Stable footprint, cable pass-through at the back.",
        "price_cents": 2799,
        "image_url": "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=600&h=600&fit=crop",
        "category": "3D Prints",
        "stock": 30,
    },
    {
        "slug": "thread-spool-blocker",
        "name": "Sewing Spool Blocker",
        "description": "Keeps thread spools from unravelling in the sewing box. A small Print Me Maybe utility print.",
        "price_cents": 999,
        "image_url": "https://images.unsplash.com/photo-1452860606245-08befc0ff44b?w=600&h=600&fit=crop",
        "category": "3D Prints",
        "stock": 80,
    },
    {
        "slug": "oak-coaster-set",
        "name": "Engraved Oak Coaster Set",
        "description": "Set of four oak coasters, laser-engraved by LaserCraft 27. Add a monogram or short quote at checkout notes.",
        "price_cents": 2299,
        "image_url": "https://images.unsplash.com/photo-1610701596007-11502861dcfa?w=600&h=600&fit=crop",
        "category": "Laser Engraving",
        "stock": 36,
    },
    {
        "slug": "cutting-board",
        "name": "Personalized Cutting Board",
        "description": "Hardwood board with a name, date, or family recipe heading engraved. Food-safe oil finish.",
        "price_cents": 4999,
        "image_url": "https://images.unsplash.com/photo-1590794056226-79ef3a8147e1?w=600&h=600&fit=crop",
        "category": "Laser Engraving",
        "stock": 22,
    },
    {
        "slug": "name-plaque",
        "name": "Custom Door Plaque",
        "description": "Laser-cut and engraved name plaque for a studio, nursery, or front door. Choose wood or acrylic.",
        "price_cents": 1999,
        "image_url": "https://images.unsplash.com/photo-1565193566173-7a0ee3dbe50e?w=600&h=600&fit=crop",
        "category": "Laser Engraving",
        "stock": 40,
    },
    {
        "slug": "leather-key-fob",
        "name": "Engraved Leather Key Fob",
        "description": "Vegetable-tanned leather fob with initials or a short word burned in by LaserCraft 27.",
        "price_cents": 1699,
        "image_url": "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?w=600&h=600&fit=crop",
        "category": "Laser Engraving",
        "stock": 48,
    },
    {
        "slug": "slate-photo",
        "name": "Photo-Engraved Slate",
        "description": "Your photo etched onto natural slate. Send the image after checkout — high-contrast pictures work best.",
        "price_cents": 3499,
        "image_url": "https://images.unsplash.com/photo-1541123437800-1bb1317badc2?w=600&h=600&fit=crop",
        "category": "Laser Engraving",
        "stock": 18,
    },
    {
        "slug": "family-name-sign",
        "name": "Large Family Name Sign",
        "description": "Statement wall sign with family name and established year. Laser-cut lettering on stained wood.",
        "price_cents": 7900,
        "image_url": "https://images.unsplash.com/photo-1513519245088-0e12902e35ca?w=600&h=600&fit=crop",
        "category": "Laser Engraving",
        "stock": 12,
    },
]


def seed_products() -> None:
    """Insert catalog when empty; replace leftover demo SKUs from earlier shop versions."""
    expected_slugs = {item["slug"] for item in CATALOG}
    with get_connection() as conn:
        rows = conn.execute("SELECT slug FROM products").fetchall()
        existing = {row["slug"] for row in rows}
        if existing == expected_slugs:
            return

        conn.execute("DELETE FROM order_items")
        conn.execute("DELETE FROM orders")
        conn.execute("DELETE FROM products")
        conn.executemany(
            """
            INSERT INTO products (slug, name, description, price_cents, image_url, category, stock)
            VALUES (:slug, :name, :description, :price_cents, :image_url, :category, :stock)
            """,
            CATALOG,
        )
