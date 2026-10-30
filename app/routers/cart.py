from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.deps import Conn, CurrentUser
from app.http import flash_redirect
from app.repositories import cart
from app.services.cart_service import (
    CartError,
    active_lines,
    add_to_cart,
    change_quantity,
    lines_total,
)
from app.services.checkout import CheckoutError, checkout
from app.web import render

router = APIRouter()


@router.get("/cart", response_class=HTMLResponse)
def cart_page(request: Request, conn: Conn, user: CurrentUser) -> HTMLResponse:
    lines = active_lines(conn, user.id)
    total = lines_total(lines)
    return render(request, conn, "cart.html", user=user, lines=lines, total=total)


@router.post("/cart/items")
def add_item(
    request: Request,
    conn: Conn,
    user: CurrentUser,
    product_id: Annotated[int, Form()],
    quantity: Annotated[int, Form()] = 1,
) -> RedirectResponse:
    try:
        message = add_to_cart(conn, user.id, product_id, quantity)
    except CartError as exc:
        message = exc.message
    return flash_redirect(request, conn, "/cart", message)


@router.post("/cart/items/{item_id}")
def update_item(
    conn: Conn,
    user: CurrentUser,
    item_id: int,
    quantity: Annotated[int, Form()] = 1,
) -> RedirectResponse:
    change_quantity(conn, user.id, item_id, quantity)
    return RedirectResponse("/cart", status_code=303)


@router.post("/cart/items/{item_id}/delete")
def delete_item(conn: Conn, user: CurrentUser, item_id: int) -> RedirectResponse:
    from app.db import transaction

    with transaction(conn):
        cart.delete_item(conn, user.id, item_id)
    return RedirectResponse("/cart", status_code=303)


@router.get("/checkout", response_class=HTMLResponse)
def checkout_page(request: Request, conn: Conn, user: CurrentUser) -> Response:
    lines = active_lines(conn, user.id)
    if not lines:
        return RedirectResponse("/cart", status_code=303)
    total = lines_total(lines)
    return render(request, conn, "checkout.html", user=user, lines=lines, total=total)


@router.post("/checkout", response_class=HTMLResponse)
def submit_checkout(
    request: Request,
    conn: Conn,
    user: CurrentUser,
    receiver_name: Annotated[str, Form()] = "",
    receiver_phone: Annotated[str, Form()] = "",
    address: Annotated[str, Form()] = "",
    payment_method: Annotated[str, Form()] = "card",
) -> Response:
    try:
        order_no = checkout(
            conn,
            user.id,
            receiver_name=receiver_name,
            receiver_phone=receiver_phone,
            address=address,
            payment_method=payment_method,
        )
    except CheckoutError as exc:
        if exc.message.startswith("장바구니가 비어"):
            return RedirectResponse("/cart", status_code=303)
        lines = active_lines(conn, user.id)
        total = lines_total(lines)
        return render(
            request,
            conn,
            "checkout.html",
            user=user,
            lines=lines,
            total=total,
            error=exc.message,
            receiver_name=receiver_name,
            receiver_phone=receiver_phone,
            address=address,
            payment_method=payment_method,
        )
    return RedirectResponse(f"/orders/{order_no}", status_code=303)
