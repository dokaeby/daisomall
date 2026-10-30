from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.deps import Conn, CurrentUser
from app.order_status import STATUS_LABELS, timeline_steps
from app.repositories.orders import get_order, list_order_items, list_orders
from app.web import render

router = APIRouter()


@router.get("/orders", response_class=HTMLResponse)
def order_list(request: Request, conn: Conn, user: CurrentUser) -> HTMLResponse:
    return render(
        request,
        conn,
        "orders.html",
        user=user,
        orders=list_orders(conn, user.id),
        status_labels=STATUS_LABELS,
    )


@router.get("/orders/{order_no}", response_class=HTMLResponse)
def order_detail(request: Request, conn: Conn, user: CurrentUser, order_no: str) -> HTMLResponse:
    order = get_order(conn, order_no, user.id)
    if order is None:
        raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다.")
    return render(
        request,
        conn,
        "order_detail.html",
        user=user,
        order=order,
        items=list_order_items(conn, order.id),
        timeline=timeline_steps(order.status),
        status_label=STATUS_LABELS.get(order.status, order.status),
    )
