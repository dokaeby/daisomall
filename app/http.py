from __future__ import annotations

from fastapi import Request
from fastapi.responses import RedirectResponse

from app.auth.deps import SESSION_COOKIE
from app.auth.service import set_flash


def flash_redirect(
    request: Request,
    conn: object,
    target: str,
    message: str,
    *,
    status_code: int = 303,
) -> RedirectResponse:
    set_flash(conn, request.cookies.get(SESSION_COOKIE), message)
    return RedirectResponse(target, status_code=status_code)
