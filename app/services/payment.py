from __future__ import annotations

from dataclasses import dataclass

ALLOWED_METHODS = {"card", "bank_transfer"}


@dataclass(frozen=True)
class PaymentResult:
    ok: bool
    message: str


class MockPaymentGateway:
    """실 PG 연동 전 단계의 결정적 모의 결제.

    한도 초과와 미지원 수단만 실패한다. 같은 입력이면 항상 같은 결과가 나온다.
    """

    def __init__(self, limit: int = 1_000_000) -> None:
        self.limit = limit

    def charge(self, amount: int, method: str) -> PaymentResult:
        if method not in ALLOWED_METHODS:
            return PaymentResult(False, "지원하지 않는 결제 수단입니다.")
        if amount > self.limit:
            return PaymentResult(False, f"1회 결제 한도({self.limit:,}원)를 초과했습니다.")
        return PaymentResult(True, "결제가 완료되었습니다.")
