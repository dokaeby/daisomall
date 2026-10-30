from __future__ import annotations

import secrets
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.auth.passwords import hash_password, verify_password
from app.db import now_iso, transaction
from app.repositories import users
from app.validators import EMAIL_RE, PHONE_RE


class AuthError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class User:
    id: int
    email: str
    name: str
    phone: str | None
    is_admin: bool


def _to_user(row: object) -> User:
    return User(
        id=row["id"],
        email=row["email"],
        name=row["name"],
        phone=row["phone"],
        is_admin=bool(row["is_admin"]),
    )


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _validate_signup(email: str, password: str, name: str, phone: str | None) -> list[str]:
    errors: list[str] = []
    if not EMAIL_RE.match(email):
        errors.append("이메일 형식이 올바르지 않습니다.")
    if len(password) < 8:
        errors.append("비밀번호는 8자 이상이어야 합니다.")
    elif len(password) > 72:
        errors.append("비밀번호는 72자 이하여야 합니다.")
    if not 1 <= len(name) <= 50:
        errors.append("이름은 1~50자로 입력해 주세요.")
    if phone is not None and not PHONE_RE.match(phone):
        errors.append("연락처는 숫자와 하이픈 10~13자로 입력해 주세요.")
    return errors


def sign_up(
    conn: object,
    *,
    email: str,
    password: str,
    name: str,
    phone: str | None,
) -> int:
    email = normalize_email(email)
    name = name.strip()
    phone = (phone or "").strip() or None

    errors = _validate_signup(email, password, name, phone)
    if errors:
        raise AuthError("\n".join(errors))
    if users.find_by_email(conn, email) is not None:
        raise AuthError("이미 사용 중인 이메일입니다.")

    try:
        with transaction(conn):
            return users.create(
                conn,
                email=email,
                password_hash=hash_password(password),
                name=name,
                phone=phone,
            )
    except sqlite3.IntegrityError as exc:
        raise AuthError("이미 사용 중인 이메일입니다.") from exc


def sign_in(
    conn: object,
    *,
    email: str,
    password: str,
    session_days: int = 7,
) -> str:
    row = users.find_by_email(conn, normalize_email(email))
    if (
        row is None
        or row["deleted_at"] is not None
        or not verify_password(password, row["password_hash"])
    ):
        raise AuthError("이메일 또는 비밀번호가 올바르지 않습니다.")

    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(UTC) + timedelta(days=session_days)).replace(microsecond=0)
    with transaction(conn):
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, row["id"], now_iso(), expires_at.isoformat()),
        )
    return token


def sign_out(conn: object, token: str | None) -> None:
    if not token:
        return
    with transaction(conn):
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def current_user(conn: object, token: str | None) -> User | None:
    if not token:
        return None
    row = conn.execute(
        "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id"
        " WHERE s.token = ? AND s.expires_at > ? AND u.deleted_at IS NULL",
        (token, now_iso()),
    ).fetchone()
    if row is not None:
        return _to_user(row)
    conn.execute("DELETE FROM sessions WHERE token = ? AND expires_at <= ?", (token, now_iso()))
    return None


def set_flash(conn: object, token: str | None, message: str) -> None:
    if not token:
        return
    conn.execute("UPDATE sessions SET flash = ? WHERE token = ?", (message, token))


def pop_flash(conn: object, token: str | None) -> str | None:
    if not token:
        return None
    row = conn.execute("SELECT flash FROM sessions WHERE token = ?", (token,)).fetchone()
    if row is None or not row["flash"]:
        return None
    conn.execute("UPDATE sessions SET flash = NULL WHERE token = ?", (token,))
    return str(row["flash"])


def delete_account(conn: object, *, user_id: int, password: str) -> None:
    row = users.find_by_id(conn, user_id)
    if row is None or not verify_password(password, row["password_hash"]):
        raise AuthError("비밀번호가 올바르지 않습니다.")

    with transaction(conn):
        conn.execute(
            "UPDATE users SET deleted_at = ?, email = ?, password_hash = ?, name = ?, phone = NULL"
            " WHERE id = ?",
            (
                now_iso(),
                f"deleted+{user_id}@invalid.local",
                hash_password(secrets.token_hex(16)),
                "탈퇴회원",
                user_id,
            ),
        )
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
