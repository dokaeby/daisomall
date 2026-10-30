from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.db import now_iso
from app.repositories.cart import CartLine


@dataclass(frozen=True)
class OrderItem:
    product_id: int
    product_name: str
    unit_price: int
    quantity: int

    @property
    def subtotal(self) -> int:
        return self.unit_price * self.quantity


@dataclass(frozen=True)
class Order:
    id: int
    order_no: str
    status: str
    total_amount: int
    receiver_name: str
    receiver_phone: str
    address: str
    payment_method: str
    paid_at: str | None
    carrier: str | None
    tracking_no: str | None
    created_at: str


def _to_order(row: object) -> Order:
    return Order(
        id=row["id"],
        order_no=row["order_no"],
        status=row["status"],
        total_amount=row["total_amount"],
        receiver_name=row["receiver_name"],
        receiver_phone=row["receiver_phone"],
        address=row["address"],
        payment_method=row["payment_method"],
        paid_at=row["paid_at"],
        carrier=row["carrier"],
        tracking_no=row["tracking_no"],
        created_at=row["created_at"],
    )


def _next_order_no(conn: object) -> str:
    # 주문번호는 사용자가 읽는 값이라 UTC가 아닌 로컬 날짜를 쓴다.
    prefix = datetime.now().strftime("%Y%m%d")
    row = conn.execute(
        "SELECT order_no FROM orders WHERE order_no LIKE ? ORDER BY order_no DESC LIMIT 1",
        (f"{prefix}-%",),
    ).fetchone()
    sequence = int(row["order_no"].split("-")[1]) + 1 if row is not None else 1
    return f"{prefix}-{sequence:04d}"


def create_order(
    conn: object,
    *,
    user_id: int,
    lines: list[CartLine],
    receiver_name: str,
    receiver_phone: str,
    address: str,
    payment_method: str,
) -> str:
    """Create an order with items and return the order number."""
    order_no = _next_order_no(conn)
    total = sum(line.subtotal for line in lines)

    cursor = conn.execute(
        "INSERT INTO orders (order_no, user_id, status, total_amount, receiver_name,"
        " receiver_phone, address, payment_method, created_at)"
        " VALUES (?, ?, 'PENDING', ?, ?, ?, ?, ?, ?) RETURNING id",
        (
            order_no,
            user_id,
            total,
            receiver_name,
            receiver_phone,
            address,
            payment_method,
            now_iso(),
        ),
    )
    order_id = int(cursor.fetchone()["id"])
    for line in lines:
        conn.execute(
            "INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity)"
            " VALUES (?, ?, ?, ?, ?)",
            (order_id, line.product.id, line.product.name, line.product.price, line.quantity),
        )
    return order_no


def get_order(conn: object, order_no: str, user_id: int | None = None) -> Order | None:
    if user_id is None:
        row = conn.execute("SELECT * FROM orders WHERE order_no = ?", (order_no,)).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM orders WHERE order_no = ? AND user_id = ?", (order_no, user_id)
        ).fetchone()
    return _to_order(row) if row is not None else None


def list_orders(conn: object, user_id: int) -> list[Order]:
    rows = conn.execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (user_id,)
    ).fetchall()
    return [_to_order(row) for row in rows]


def list_all_orders(conn: object) -> list[Order]:
    rows = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    return [_to_order(row) for row in rows]


def list_order_items(conn: object, order_id: int) -> list[OrderItem]:
    rows = conn.execute(
        "SELECT product_id, product_name, unit_price, quantity FROM order_items"
        " WHERE order_id = ? ORDER BY id",
        (order_id,),
    ).fetchall()
    return [
        OrderItem(
            product_id=row["product_id"],
            product_name=row["product_name"],
            unit_price=row["unit_price"],
            quantity=row["quantity"],
        )
        for row in rows
    ]


def mark_paid(conn: object, order_no: str) -> None:
    conn.execute(
        "UPDATE orders SET status = 'PAID', paid_at = ? WHERE order_no = ?",
        (now_iso(), order_no),
    )


def decrement_stock(conn: object, product_id: int, quantity: int) -> bool:
    cursor = conn.execute(
        "UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?",
        (quantity, product_id, quantity),
    )
    return cursor.rowcount == 1


def set_shipped(conn: object, order_no: str, carrier: str, tracking_no: str) -> bool:
    cursor = conn.execute(
        "UPDATE orders SET status = 'SHIPPED', carrier = ?, tracking_no = ?"
        " WHERE order_no = ? AND status IN ('PAID', 'PREPARING')",
        (carrier, tracking_no, order_no),
    )
    return cursor.rowcount == 1


def set_delivered(conn: object, order_no: str) -> bool:
    cursor = conn.execute(
        "UPDATE orders SET status = 'DELIVERED' WHERE order_no = ? AND status = 'SHIPPED'",
        (order_no,),
    )
    return cursor.rowcount == 1
