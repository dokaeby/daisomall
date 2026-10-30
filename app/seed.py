from __future__ import annotations

from app.auth.passwords import hash_password
from app.config import Settings, load_settings
from app.db import connect, init_db, transaction
from app.repositories import users
from app.repositories.products import create_product

CATALOG: list[tuple[str, str, int, str, int, str]] = [
    ("주방 수세미", "3개입, 양면 사용", 1000, "주방", 40, "🧽"),
    ("실리콘 주걱", "내열 230도", 2000, "주방", 25, "🥄"),
    ("밀폐 용기", "500ml, 전자레인지 사용 가능", 1500, "주방", 30, "🥡"),
    ("주방 타이머", "60분 타이머", 3000, "주방", 15, "⏲️"),
    ("욕실 샴푸", "500ml, 약산성", 3000, "욕실", 20, "🧴"),
    ("때수건", "이태리 타월 2매", 1200, "욕실", 50, "🧼"),
    ("욕실 매트", "미끄럼 방지", 4000, "욕실", 12, "🛁"),
    ("칫솔 4개입", "부드러운 모", 2000, "욕실", 35, "🪥"),
    ("볼펜 3색", "0.5mm", 1500, "문구", 60, "🖊️"),
    ("노트 A5", "줄노트 60매", 1000, "문구", 45, "📒"),
    ("포스트잇", "76x76mm 100매", 1800, "문구", 28, "🗒️"),
    ("가위", "사무용 17cm", 2500, "문구", 18, "✂️"),
    ("극세사 걸레", "3매입", 2000, "청소", 40, "🧹"),
    ("청소용 스펀지", "5개입", 1000, "청소", 55, "🧽"),
    ("세탁 세제", "1L, 액체", 3500, "청소", 22, "🧺"),
    ("쓰레기봉투", "20L 10매", 1500, "청소", 33, "🗑️"),
    ("수납 바구니", "소형, PP", 2000, "수납", 26, "🧺"),
    ("옷걸이 10개", "논슬립", 3000, "수납", 20, "👔"),
    ("압축 팩", "3매입", 2500, "수납", 24, "📦"),
    ("선반 정리함", "2단", 4500, "수납", 10, "🗄️"),
    ("양말 3켤레", "면 100%", 3000, "패션", 30, "🧦"),
    ("마스크 10매", "일회용", 2000, "패션", 50, "😷"),
    ("장갑", "면 작업장갑", 1500, "패션", 40, "🧤"),
    ("우산", "3단 자동", 5000, "패션", 8, "☂️"),
]


def seed(settings: Settings) -> None:
    init_db(settings.database_path, settings.database_type)
    conn = connect(settings.database_path)
    try:
        with transaction(conn):
            if users.find_by_email(conn, settings.admin_email.lower()) is None:
                users.create(
                    conn,
                    email=settings.admin_email.lower(),
                    password_hash=hash_password(settings.admin_password),
                    name="관리자",
                    phone=None,
                    is_admin=True,
                )
            count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            if count == 0:
                for name, description, price, category, stock, emoji in CATALOG:
                    create_product(
                        conn,
                        name=name,
                        description=description,
                        price=price,
                        category=category,
                        stock=stock,
                        emoji=emoji,
                    )
    finally:
        conn.close()


if __name__ == "__main__":
    seed(load_settings())
    print("시드 데이터를 준비했습니다.")
