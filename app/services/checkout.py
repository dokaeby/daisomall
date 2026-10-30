from __future__ import annotations

from app.db import transaction
from app.repositories import cart, orders
from app.services.cart_service import active_lines
from app.services.payment import MockPaymentGateway
from app.validators import PHONE_RE


class CheckoutError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _validate_shipping(receiver_name: str, receiver_phone: str, address: str) -> None:
    if not receiver_name.strip():
        raise CheckoutError("받는 사람 이름을 입력해 주세요.")
    if not PHONE_RE.match(receiver_phone.strip()):
        raise CheckoutError("연락처를 확인해 주세요.")
    if not address.strip():
        raise CheckoutError("주소를 입력해 주세요.")


def checkout(
    conn: object,
    user_id: int,
    *,
    receiver_name: str,
    receiver_phone: str,
    address: str,
    payment_method: str,
    gateway: MockPaymentGateway | None = None,
) -> str:
    gateway = gateway or MockPaymentGateway()
    with transaction(conn):
        lines = active_lines(conn, user_id)
        if not lines:
            raise CheckoutError("장바구니가 비어 있습니다.")
        _validate_shipping(receiver_name, receiver_phone, address)

        order_no = orders.create_order(
            conn,
            user_id=user_id,
            lines=lines,
            receiver_name=receiver_name.strip(),
            receiver_phone=receiver_phone.strip(),
            address=address.strip(),
            payment_method=payment_method,
        )

        # 모의 게이트웨이는 부수효과가 없어 재고 확보보다 먼저 호출해도 안전하다.
        # 실 PG로 바꿀 때는 승인/캡처를 재고 확보 이후로 옮긴다.
        result = gateway.charge(sum(line.subtotal for line in lines), payment_method)
        if not result.ok:
            raise CheckoutError(result.message)

        for line in lines:
            if not orders.decrement_stock(conn, line.product.id, line.quantity):
                raise CheckoutError(f"재고가 부족한 상품이 있습니다: {line.product.name}")

        orders.mark_paid(conn, order_no)
        cart.clear_cart(conn, user_id)
    return order_no
