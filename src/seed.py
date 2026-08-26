"""Seed catalog from @print.me.maybe posts and LaserCraft 27 custom work."""

from __future__ import annotations

from src.db import get_connection

# 3D listings use captions and euro prices from public @print.me.maybe posts.
# Laser listings are custom-order SKUs; @lasercraft.27 is login-walled so photos
# are branded placeholders until real studio shots are added.
CATALOG = [
    {
        "slug": "magical-world-bookshelf",
        "name": "Magical World Bookshelf Decor",
        "description": "3D-printed bookshelf scene inspired by a world of wonder and adventure. Perfect for book lovers. Colour on request — add it in the order notes or DM @print.me.maybe.",
        "price_cents": 1600,
        "image_url": "/static/images/products/magical-world.jpg",
        "category": "3D Prints",
        "stock": 18,
    },
    {
        "slug": "glasses-case",
        "name": "Floral Glasses Case",
        "description": "Lightweight 3D-printed case for prescription glasses or sunglasses, with an embossed floral pattern. Protects from scratches and knocks. Available in several colours — tell us your favourite in the order notes.",
        "price_cents": 400,
        "image_url": "/static/images/products/glasses-case.jpg",
        "category": "3D Prints",
        "stock": 40,
    },
    {
        "slug": "scrunchie-holder",
        "name": "Scrunchie Holder",
        "description": "Holds multiple scrunchies on an arch, with a tray for clips and small accessories. For the bathroom, vanity, or bedroom. Pick a colour in the order notes.",
        "price_cents": 600,
        "image_url": "/static/images/products/scrunchie-holder.jpg",
        "category": "3D Prints",
        "stock": 28,
    },
    {
        "slug": "lip-balm-holder-set",
        "name": "Lip Balm Holder & Name Keychain",
        "description": "Set with a 3D-printed lip balm holder and a custom name keychain. Choose the name and colours in the order notes. Made for bags, keys, or backpacks.",
        "price_cents": 700,
        "image_url": "/static/images/products/lip-balm-holder.jpg",
        "category": "3D Prints",
        "stock": 35,
    },
    {
        "slug": "magic-bookshelf-decor",
        "name": "Wizard Bookshelf Decor",
        "description": "Matte-black bookshelf piece with a flying wizard and castle silhouette. A small gift for fantasy readers. Colour on request.",
        "price_cents": 700,
        "image_url": "/static/images/products/magic-bookshelf.jpg",
        "category": "3D Prints",
        "stock": 22,
    },
    {
        "slug": "minas-tirith",
        "name": "Minas Tirith",
        "description": "Detailed 3D print of the White City of Gondor — a shelf or desk collectible for Lord of the Rings fans.",
        "price_cents": 1000,
        "image_url": "/static/images/products/minas-tirith.jpg",
        "category": "3D Prints",
        "stock": 16,
    },
    {
        "slug": "funny-desk-signs",
        "name": "Funny Desk Signs (5-pack)",
        "description": "Five small 3D-printed quote signs for a desk or shelf. Pick quotes and colours in the order notes — any five pieces for this price.",
        "price_cents": 300,
        "image_url": "/static/images/products/funny-signs.jpg",
        "category": "3D Prints",
        "stock": 50,
    },
    {
        "slug": "articulated-dragon",
        "name": "Articulated Dragon",
        "description": "Poseable 3D-printed dragon for play, décor, or gifting. Colours can be customised — add your preference in the order notes.",
        "price_cents": 1300,
        "image_url": "/static/images/products/dragon.jpg",
        "category": "3D Prints",
        "stock": 20,
    },
    {
        "slug": "dragon-egg",
        "name": "Dragon Egg",
        "description": "Matching 3D-printed dragon egg. Pair it with the articulated dragon, or order the set below and save.",
        "price_cents": 1200,
        "image_url": "/static/images/products/dragon-egg.jpg",
        "category": "3D Prints",
        "stock": 20,
    },
    {
        "slug": "dragon-egg-set",
        "name": "Dragon & Egg Set",
        "description": "Articulated dragon plus matching egg as a set. Colours customisable. A gift for fantasy fans of any age.",
        "price_cents": 2000,
        "image_url": "/static/images/products/dragon-egg.jpg",
        "category": "3D Prints",
        "stock": 14,
    },
    {
        "slug": "custom-cake-topper",
        "name": "Custom Cake Topper",
        "description": "Made-to-order topper for a wedding, baptism, birthday, or baby shower. Add names, dates, and the design in the order notes. Starting price — we confirm complex designs by DM.",
        "price_cents": 1000,
        "image_url": "/static/images/products/cake-topper.jpg",
        "category": "3D Prints",
        "stock": 30,
    },
    {
        "slug": "oak-coaster-set",
        "name": "Engraved Oak Coaster Set",
        "description": "Set of four oak coasters, laser-engraved by LaserCraft 27. Add a monogram or short quote in the order notes or DM @lasercraft.27. Photo coming — see Instagram for recent work.",
        "price_cents": 2200,
        "image_url": "/static/images/products/laser-coasters.svg",
        "category": "Laser Engraving",
        "stock": 24,
    },
    {
        "slug": "cutting-board",
        "name": "Personalized Cutting Board",
        "description": "Hardwood board with a name, date, or heading engraved. Food-safe oil finish. Send the text after checkout. Photo coming — see @lasercraft.27.",
        "price_cents": 4500,
        "image_url": "/static/images/products/laser-board.svg",
        "category": "Laser Engraving",
        "stock": 12,
    },
    {
        "slug": "name-plaque",
        "name": "Custom Door Plaque",
        "description": "Laser-cut and engraved name plaque for a studio, nursery, or front door. Wood or acrylic. Photo coming — see @lasercraft.27.",
        "price_cents": 2000,
        "image_url": "/static/images/products/laser-plaque.svg",
        "category": "Laser Engraving",
        "stock": 20,
    },
    {
        "slug": "family-name-sign",
        "name": "Large Family Name Sign",
        "description": "Statement wall sign with family name and established year. Laser-cut lettering on stained wood. Photo coming — see @lasercraft.27.",
        "price_cents": 4500,
        "image_url": "/static/images/products/laser-sign.svg",
        "category": "Laser Engraving",
        "stock": 8,
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
