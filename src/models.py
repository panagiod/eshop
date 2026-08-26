"""Domain types and formatting helpers for the storefront."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def format_money(cents: int) -> str:
    """Render integer cents as a USD string for templates."""
    return f"${cents / 100:.2f}"


@dataclass(frozen=True)
class Product:
    """A sellable item from the catalog."""

    id: int
    slug: str
    name: str
    description: str
    price_cents: int
    image_url: str
    category: str
    stock: int

    @classmethod
    def from_row(cls, row: Any) -> "Product":
        return cls(
            id=row["id"],
            slug=row["slug"],
            name=row["name"],
            description=row["description"],
            price_cents=row["price_cents"],
            image_url=row["image_url"],
            category=row["category"],
            stock=row["stock"],
        )

    @property
    def price_display(self) -> str:
        return format_money(self.price_cents)


@dataclass(frozen=True)
class CartLine:
    """One product line in the session cart."""

    product: Product
    quantity: int

    @property
    def line_total_cents(self) -> int:
        return self.product.price_cents * self.quantity

    @property
    def line_total_display(self) -> str:
        return format_money(self.line_total_cents)
