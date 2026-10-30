from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.deps import Conn, OptionalUser
from app.repositories.products import (
    PER_PAGE,
    get_product,
    list_categories,
    list_products,
    page_count,
)
from app.web import render

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    conn: Conn,
    user: OptionalUser,
    q: str | None = None,
    category: str | None = None,
    page: int = 1,
) -> HTMLResponse:
    products, total = list_products(conn, q=q, category=category, page=page)
    return render(
        request,
        conn,
        "index.html",
        user=user,
        products=products,
        total=total,
        categories=list_categories(conn),
        q=q or "",
        category=category or "",
        page=max(1, page),
        total_pages=page_count(total, PER_PAGE),
    )


@router.get("/products/{product_id}", response_class=HTMLResponse)
def product_detail(
    request: Request,
    conn: Conn,
    user: OptionalUser,
    product_id: int,
) -> HTMLResponse:
    product = get_product(conn, product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    return render(request, conn, "product_detail.html", user=user, product=product)
