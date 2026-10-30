from __future__ import annotations


def test_add_item_and_duplicate_merges_quantity(client, seeded, login):
    login()
    client.post("/cart/items", data={"product_id": 1, "quantity": 2})
    client.post("/cart/items", data={"product_id": 1, "quantity": 3})
    res = client.get("/cart")
    assert res.text.count("주방 수세미") == 1
    assert "5,000원" in res.text


def test_quantity_is_clamped_to_stock(client, seeded, login):
    login()
    client.post("/cart/items", data={"product_id": 1, "quantity": 999})
    assert "10,000원" in client.get("/cart").text


def test_zero_quantity_is_clamped_to_one(client, seeded, login):
    login()
    client.post("/cart/items", data={"product_id": 1, "quantity": 0})
    assert "1,000원" in client.get("/cart").text


def test_sold_out_product_is_not_added(client, seeded, login, db):
    from app.db import transaction

    with transaction(db):
        db.execute("UPDATE products SET stock = 0 WHERE id = 2")
    login()
    client.post("/cart/items", data={"product_id": 2, "quantity": 1})
    assert "장바구니가 비어 있습니다" in client.get("/cart").text


def test_update_and_delete_item(client, seeded, login):
    login()
    client.post("/cart/items", data={"product_id": 1, "quantity": 1})
    client.post("/cart/items/1", data={"quantity": 4})
    assert "4,000원" in client.get("/cart").text
    client.post("/cart/items/1/delete")
    assert "장바구니가 비어 있습니다" in client.get("/cart").text


def test_cannot_touch_other_users_cart(client, seeded, login, signup, db):
    login()
    client.post("/cart/items", data={"product_id": 1, "quantity": 1})
    client.post("/logout")

    signup(email="b@example.com", name="김철수")
    client.post("/cart/items", data={"product_id": 1, "quantity": 3})
    client.post("/cart/items/1", data={"quantity": 9})
    client.post("/cart/items/1/delete")

    rows = db.execute("SELECT user_id, quantity FROM cart_items ORDER BY id").fetchall()
    assert [(r["user_id"], r["quantity"]) for r in rows] == [(1, 1), (2, 3)]
