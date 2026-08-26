"""Domain types and formatting helpers for the storefront."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ORDER_STATUSES = ("new", "in_progress", "ready", "shipped", "cancelled")
ORDER_STATUS_LABELS = {
    "new": "New",
    "in_progress": "In progress",
    "ready": "Ready to ship",
    "shipped": "Shipped",
    "cancelled": "Cancelled",
}

FREE_SHIPPING_THRESHOLD_CENTS = 7500
STANDARD_SHIPPING_CENTS = 599


def format_money(cents: int) -> str:
    """Render integer cents as a USD string for templates."""
    return f"${cents / 100:.2f}"


def shipping_cents(subtotal_cents: int) -> int:
    """Standard shipping unless the cart subtotal qualifies for free shipping."""
    if subtotal_cents >= FREE_SHIPPING_THRESHOLD_CENTS:
        return 0
    return STANDARD_SHIPPING_CENTS


def order_total_cents(subtotal_cents: int) -> int:
    """Subtotal plus shipping for checkout and order persistence."""
    return subtotal_cents + shipping_cents(subtotal_cents)


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


@dataclass(frozen=True)
class OrderItem:
    """One persisted line on a completed order."""

    product_name: str
    quantity: int
    unit_price_cents: int

    @property
    def line_total_cents(self) -> int:
        return self.unit_price_cents * self.quantity

    @property
    def line_total_display(self) -> str:
        return format_money(self.line_total_cents)


@dataclass(frozen=True)
class Order:
    """A placed order with line items for the confirmation page."""

    id: int
    customer_name: str
    customer_email: str
    shipping_address: str
    total_cents: int
    created_at: str
    items: list[OrderItem]
    status: str = "new"
    notes: str = ""

    @property
    def status_label(self) -> str:
        return ORDER_STATUS_LABELS.get(self.status, self.status)

    @property
    def subtotal_cents(self) -> int:
        return sum(item.line_total_cents for item in self.items)

    @property
    def shipping_cents(self) -> int:
        return max(0, self.total_cents - self.subtotal_cents)

    @property
    def total_display(self) -> str:
        return format_money(self.total_cents)
