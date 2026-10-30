from __future__ import annotations

from typing import Annotated
from urllib.parse import quote

from fastapi import Depends, HTTPException, Request

from app.auth.service import User, current_user
from app.db import get_db

SESSION_COOKIE = "sid"


def safe_next(value: str | None) -> str:
    if not value:
        return "/"
    value = value.strip()
    if not value.startswith("/") or value.startswith("//") or "\\" in value:
        return "/"
    # 브라우저가 URL에서 제거하는 제어문자는 검증 전에 거른다(//evil.com 우회 방지).
    if any(character < " " or character == "\x7f" for character in value):
        return "/"
    return value


def current_user_dep(
    request: Request,
    conn: Annotated[object, Depends(get_db)],
) -> User | None:
    return current_user(conn, request.cookies.get(SESSION_COOKIE))


def require_user(
    request: Request,
    conn: Annotated[object, Depends(get_db)],
) -> User:
    user = current_user(conn, request.cookies.get(SESSION_COOKIE))
    if user is None:
        target = request.url.path
        if request.url.query:
            target = f"{target}?{request.url.query}"
        raise HTTPException(
            status_code=303,
            headers={"Location": f"/login?next={quote(target, safe='')}"},
        )
    return user


def require_admin(
    request: Request,
    conn: Annotated[object, Depends(get_db)],
) -> User:
    user = require_user(request, conn)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="관리자만 접근할 수 있습니다.")
    return user
