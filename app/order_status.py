from __future__ import annotations

# Single source for order status labels and timeline.
# Routers and templates use these instead of duplicating.
TIMELINE: list[tuple[str, str]] = [
    ("PAID", "결제완료"),
    ("PREPARING", "상품준비중"),
    ("SHIPPED", "배송중"),
    ("DELIVERED", "배송완료"),
]
STATUS_LABELS: dict[str, str] = {code: label for code, label in TIMELINE} | {
    "PENDING": "결제대기",
    "CANCELLED": "취소됨",
}


def timeline_steps(status: str) -> list[tuple[str, bool]]:
    reached = [code for code, _ in TIMELINE]
    index = reached.index(status) if status in reached else -1
    return [(label, position <= index) for position, (_, label) in enumerate(TIMELINE)]
