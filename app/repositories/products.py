from __future__ import annotations

import math
from dataclasses import dataclass

from app.db import now_iso

PER_PAGE = 12


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    description: str
    price: int
    category: str
    stock: int
    emoji: str
    is_active: bool


def to_product(row: object) -> Product:
    return Product(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        price=row["price"],
        category=row["category"],
        stock=row["stock"],
        emoji=row["emoji"],
        is_active=bool(row["is_active"]),
    )


def list_products(
    conn: object,
    *,
    q: str | None = None,
    category: str | None = None,
    page: int = 1,
    per_page: int = PER_PAGE,
) -> tuple[list[Product], int]:
    where = ["is_active = 1"]
    params: list[object] = []
    if q:
        where.append("name LIKE '%' || ? || '%'")
        params.append(q.strip())
    if category:
        where.append("category = ?")
        params.append(category)
    clause = " AND ".join(where)

    total = conn.execute(f"SELECT COUNT(*) FROM products WHERE {clause}", params).fetchone()[0]
    page = max(1, page)
    rows = conn.execute(
        f"SELECT * FROM products WHERE {clause} ORDER BY id DESC LIMIT ? OFFSET ?",
        [*params, per_page, (page - 1) * per_page],
    ).fetchall()
    return [to_product(row) for row in rows], total


def page_count(total: int, per_page: int = PER_PAGE) -> int:
    return max(1, math.ceil(total / per_page))


def get_product(conn: object, product_id: int) -> Product | None:
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    return to_product(row) if row is not None else None


def list_all_active(conn: object) -> list[Product]:
    rows = conn.execute("SELECT * FROM products WHERE is_active = 1 ORDER BY id DESC").fetchall()
    return [to_product(row) for row in rows]


def list_categories(conn: object) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT category FROM products WHERE is_active = 1 ORDER BY category"
    ).fetchall()
    return [row["category"] for row in rows]


def create_product(
    conn: object,
    *,
    name: str,
    description: str,
    price: int,
    category: str,
    stock: int,
    emoji: str = "📦",
) -> int:
    """Insert a product and return its new ID.

    Uses ``RETURNING id`` for PostgreSQL compatibility (also works on SQLite 3.35+).
    """
    cursor = conn.execute(
        "INSERT INTO products (name, description, price, category, stock, emoji, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id",
        (name, description, price, category, stock, emoji or "📦", now_iso()),
    )
    return int(cursor.fetchone()["id"])
