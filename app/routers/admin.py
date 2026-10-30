from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.auth.service import User
from app.deps import AdminUser, Conn
from app.http import flash_redirect
from app.repositories.orders import list_all_orders, set_delivered, set_shipped
from app.repositories.products import create_product, list_all_active
from app.web import render

router = APIRouter(prefix="/admin")


def _products_page(
    request: Request,
    conn: object,
    user: User,
    *,
    error: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    products = list_all_active(conn)
    return render(
        request,
        conn,
        "admin_products.html",
        user=user,
        products=products,
        error=error,
        status_code=status_code,
    )


@router.get("/products", response_class=HTMLResponse)
def product_list(request: Request, conn: Conn, user: AdminUser) -> HTMLResponse:
    return _products_page(request, conn, user)


@router.post("/products", response_class=HTMLResponse)
def product_create(
    request: Request,
    conn: Conn,
    user: AdminUser,
    name: Annotated[str, Form()] = "",
    description: Annotated[str, Form()] = "",
    price: Annotated[str, Form()] = "",
    category: Annotated[str, Form()] = "",
    stock: Annotated[str, Form()] = "",
    emoji: Annotated[str, Form()] = "📦",
) -> Response:
    errors: list[str] = []
    if not name.strip():
        errors.append("상품명을 입력해 주세요.")
    if not category.strip():
        errors.append("카테고리를 입력해 주세요.")
    try:
        price_value = int(price)
        if price_value < 0:
            raise ValueError
    except ValueError:
        errors.append("가격은 0 이상의 숫자여야 합니다.")
        price_value = 0
    try:
        stock_value = int(stock)
        if stock_value < 0:
            raise ValueError
    except ValueError:
        errors.append("재고는 0 이상의 숫자여야 합니다.")
        stock_value = 0

    if errors:
        return _products_page(request, conn, user, error="\n".join(errors))

    from app.db import transaction

    with transaction(conn):
        create_product(
            conn,
            name=name.strip(),
            description=description.strip(),
            price=price_value,
            category=category.strip(),
            stock=stock_value,
            emoji=emoji.strip() or "📦",
        )
    return flash_redirect(request, conn, "/admin/products", "상품을 등록했습니다.")


@router.get("/orders", response_class=HTMLResponse)
def order_list(request: Request, conn: Conn, user: AdminUser) -> HTMLResponse:
    return render(request, conn, "admin_orders.html", user=user, orders=list_all_orders(conn))


@router.post("/orders/{order_no}/shipping")
def register_shipping(
    request: Request,
    conn: Conn,
    user: AdminUser,
    order_no: str,
    carrier: Annotated[str, Form()] = "",
    tracking_no: Annotated[str, Form()] = "",
) -> RedirectResponse:
    ok = bool(carrier.strip() and tracking_no.strip()) and set_shipped(
        conn, order_no, carrier.strip(), tracking_no.strip()
    )
    message = (
        "운송장을 등록했습니다." if ok else "운송장 등록에 실패했습니다. 상태를 확인해 주세요."
    )
    return flash_redirect(request, conn, "/admin/orders", message)


@router.post("/orders/{order_no}/delivered")
def mark_delivered(
    request: Request, conn: Conn, user: AdminUser, order_no: str
) -> RedirectResponse:
    ok = set_delivered(conn, order_no)
    message = "배송완료로 처리했습니다." if ok else "배송완료 처리에 실패했습니다."
    return flash_redirect(request, conn, "/admin/orders", message)
