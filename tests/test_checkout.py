from __future__ import annotations

from app.db import transaction


def test_checkout_creates_paid_order_and_clears_cart(client, seeded, login, db):
    login()
    client.post("/cart/items", data={"product_id": 1, "quantity": 2})
    res = client.post(
        "/checkout",
        data={
            "receiver_name": "홍길동",
            "receiver_phone": "01012345678",
            "address": "서울시 어딘가 1",
            "payment_method": "card",
        },
        follow_redirects=False,
    )
    assert res.status_code == 303
    order_no = res.headers["location"].rsplit("/", 1)[-1]

    detail = client.get(f"/orders/{order_no}")
    assert "현재 상태: 결제완료" in detail.text
    assert "2,000원" in detail.text
    assert "장바구니가 비어 있습니다" in client.get("/cart").text
    assert db.execute("SELECT stock FROM products WHERE id = 1").fetchone()["stock"] == 8


def test_order_keeps_price_and_name_snapshot(client, seeded, login, db, place_order):
    login()
    order_no = place_order()
    with transaction(db):
        db.execute("UPDATE products SET price = 9999, name = '바뀐 이름' WHERE id = 1")

    detail = client.get(f"/orders/{order_no}").text
    assert "1,000원" in detail
    assert "바뀐 이름" not in detail


def test_checkout_with_empty_cart_redirects_to_cart(client, seeded, login):
    login()
    res = client.post(
        "/checkout",
        data={
            "receiver_name": "홍",
            "receiver_phone": "01012345678",
            "address": "서울",
            "payment_method": "card",
        },
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert res.headers["location"] == "/cart"


def test_insufficient_stock_rolls_back_everything(client, seeded, login, db):
    login()
    client.post("/cart/items", data={"product_id": 1, "quantity": 10})
    with transaction(db):
        db.execute("UPDATE products SET stock = 1 WHERE id = 1")

    res = client.post(
        "/checkout",
        data={
            "receiver_name": "홍",
            "receiver_phone": "01012345678",
            "address": "서울",
            "payment_method": "card",
        },
    )
    assert "재고" in res.text
    assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
    assert db.execute("SELECT stock FROM products WHERE id = 1").fetchone()["stock"] == 1


def test_payment_failure_leaves_no_order_and_no_stock_change(client, seeded, login, db):
    login()
    client.post("/cart/items", data={"product_id": 2, "quantity": 1})
    with transaction(db):
        db.execute("UPDATE products SET price = 2000000 WHERE id = 2")

    res = client.post(
        "/checkout",
        data={
            "receiver_name": "홍",
            "receiver_phone": "01012345678",
            "address": "서울",
            "payment_method": "card",
        },
    )
    assert "한도" in res.text
    assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM cart_items").fetchone()[0] == 1
    assert db.execute("SELECT stock FROM products WHERE id = 2").fetchone()["stock"] == 5


def test_zero_stock_product_blocks_checkout(client, seeded, login, db):
    login()
    client.post("/cart/items", data={"product_id": 1, "quantity": 1})
    with transaction(db):
        db.execute("UPDATE products SET stock = 0 WHERE id = 1")

    res = client.post(
        "/checkout",
        data={
            "receiver_name": "홍",
            "receiver_phone": "01012345678",
            "address": "서울",
            "payment_method": "card",
        },
    )
    assert "재고가 부족" in res.text
    assert db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0


def test_checkout_validates_shipping_fields(client, seeded, login):
    login()
    client.post("/cart/items", data={"product_id": 1, "quantity": 1})
    res = client.post(
        "/checkout",
        data={"receiver_name": "", "receiver_phone": "12", "address": "", "payment_method": "card"},
    )
    assert res.status_code == 200
    assert "받는 사람" in res.text
