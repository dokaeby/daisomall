from __future__ import annotations

from app.db import transaction
from app.repositories import cart
from app.repositories.products import get_product


class CartError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def active_lines(conn: object, user_id: int):
    """Return cart items for active products only (applies business rule once)."""
    return [line for line in cart.list_items(conn, user_id) if line.product.is_active]


def lines_total(lines):
    """Sum subtotals of a list of CartLine (replaces repeated comprehension)."""
    return sum(line.subtotal for line in lines)


def add_to_cart(conn: object, user_id: int, product_id: int, quantity: int) -> str:
    product = get_product(conn, product_id)
    if product is None or not product.is_active:
        raise CartError("판매 중지된 상품입니다.")
    if product.stock <= 0:
        return "품절된 상품입니다."

    quantity = max(1, min(quantity, product.stock))
    with transaction(conn):
        cart.add_item(conn, user_id, product_id, quantity)
    return f"{product.name} {quantity}개를 장바구니에 담았습니다."


def change_quantity(conn: object, user_id: int, item_id: int, quantity: int) -> None:
    line = next((line for line in cart.list_items(conn, user_id) if line.id == item_id), None)
    if line is None:
        return
    quantity = max(1, min(quantity, line.product.stock))
    with transaction(conn):
        cart.update_quantity(conn, user_id, item_id, quantity)
