from __future__ import annotations

from dataclasses import dataclass

from app.db import now_iso
from app.repositories.products import Product, to_product


@dataclass(frozen=True)
class CartLine:
    id: int
    product: Product
    quantity: int

    @property
    def subtotal(self) -> int:
        return self.product.price * self.quantity


def list_items(conn: object, user_id: int) -> list[CartLine]:
    rows = conn.execute(
        "SELECT c.id AS cart_id, c.quantity, p.* FROM cart_items c"
        " JOIN products p ON p.id = c.product_id"
        " WHERE c.user_id = ? ORDER BY c.id",
        (user_id,),
    ).fetchall()
    return [
        CartLine(id=row["cart_id"], product=to_product(row), quantity=row["quantity"])
        for row in rows
    ]


def add_item(conn: object, user_id: int, product_id: int, quantity: int) -> None:
    existing = conn.execute(
        "SELECT quantity FROM cart_items WHERE user_id = ? AND product_id = ?",
        (user_id, product_id),
    ).fetchone()
    if existing is None:
        conn.execute(
            "INSERT INTO cart_items (user_id, product_id, quantity, added_at) VALUES (?, ?, ?, ?)",
            (user_id, product_id, quantity, now_iso()),
        )
        return
    conn.execute(
        "UPDATE cart_items SET quantity = ? WHERE user_id = ? AND product_id = ?",
        (existing["quantity"] + quantity, user_id, product_id),
    )


def update_quantity(conn: object, user_id: int, item_id: int, quantity: int) -> bool:
    cursor = conn.execute(
        "UPDATE cart_items SET quantity = ? WHERE id = ? AND user_id = ?",
        (quantity, item_id, user_id),
    )
    return cursor.rowcount == 1


def delete_item(conn: object, user_id: int, item_id: int) -> None:
    conn.execute("DELETE FROM cart_items WHERE id = ? AND user_id = ?", (item_id, user_id))


def clear_cart(conn: object, user_id: int) -> None:
    conn.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))


def cart_count(conn: object, user_id: int) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM cart_items WHERE user_id = ?", (user_id,)
    ).fetchone()
    return int(row[0])
