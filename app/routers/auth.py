from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.auth import service
from app.auth.deps import SESSION_COOKIE, safe_next
from app.auth.service import AuthError
from app.deps import Conn, CurrentUser
from app.web import render

router = APIRouter()


def _login_response(token: str, settings, target: str) -> RedirectResponse:
    response = RedirectResponse(target, status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=settings.session_days * 86400,
        path="/",
    )
    return response


@router.get("/signup", response_class=HTMLResponse)
def signup_form(request: Request, conn: Conn) -> HTMLResponse:
    return render(request, conn, "signup.html")


@router.post("/signup", response_class=HTMLResponse)
def signup(
    request: Request,
    conn: Conn,
    email: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
    name: Annotated[str, Form()] = "",
    phone: Annotated[str, Form()] = "",
) -> Response:
    try:
        service.sign_up(conn, email=email, password=password, name=name, phone=phone)
        token = service.sign_in(
            conn,
            email=email,
            password=password,
            session_days=request.app.state.settings.session_days,
        )
    except AuthError as exc:
        return render(
            request, conn, "signup.html", error=exc.message, email=email, name=name, phone=phone
        )
    return _login_response(token, request.app.state.settings, "/")


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, conn: Conn, next: str | None = None) -> HTMLResponse:
    return render(request, conn, "login.html", next_path=safe_next(next))


@router.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    conn: Conn,
    email: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
    next_path: Annotated[str, Form(alias="next")] = "",
) -> Response:
    try:
        token = service.sign_in(
            conn,
            email=email,
            password=password,
            session_days=request.app.state.settings.session_days,
        )
    except AuthError as exc:
        return render(
            request,
            conn,
            "login.html",
            error=exc.message,
            email=email,
            next_path=safe_next(next_path),
        )
    return _login_response(token, request.app.state.settings, safe_next(next_path))


@router.post("/logout")
def logout(request: Request, conn: Conn) -> RedirectResponse:
    service.sign_out(conn, request.cookies.get(SESSION_COOKIE))
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@router.get("/mypage", response_class=HTMLResponse)
def mypage(request: Request, conn: Conn, user: CurrentUser) -> HTMLResponse:
    return render(request, conn, "mypage.html", user=user)


@router.post("/mypage/delete", response_class=HTMLResponse)
def delete_account(
    request: Request,
    conn: Conn,
    user: CurrentUser,
    password: Annotated[str, Form()] = "",
) -> Response:
    try:
        service.delete_account(conn, user_id=user.id, password=password)
    except AuthError as exc:
        return render(request, conn, "mypage.html", user=user, error=exc.message)

    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response
