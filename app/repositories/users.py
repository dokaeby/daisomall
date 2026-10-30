from __future__ import annotations

from app.db import now_iso


def find_by_email(conn: object, email: str) -> object | None:
    return conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def find_by_id(conn: object, user_id: int) -> object | None:
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def create(
    conn: object,
    *,
    email: str,
    password_hash: str,
    name: str,
    phone: str | None,
    is_admin: bool = False,
) -> int:
    """Create a user and return its ID (works for both SQLite and PostgreSQL)."""
    cursor = conn.execute(
        "INSERT INTO users (email, password_hash, name, phone, is_admin, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?) RETURNING id",
        (email, password_hash, name, phone, int(is_admin), now_iso()),
    )
    return int(cursor.fetchone()["id"])
