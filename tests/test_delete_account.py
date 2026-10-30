from __future__ import annotations


def test_delete_account_requires_correct_password(client, login):
    login()
    res = client.post("/mypage/delete", data={"password": "wrong"})
    assert "비밀번호가 올바르지 않습니다" in res.text
    assert client.get("/mypage", follow_redirects=False).status_code == 200


def test_delete_account_removes_sessions_and_blocks_login(client, login):
    login()
    client.post("/mypage/delete", data={"password": "secret123"})
    assert client.get("/mypage", follow_redirects=False).status_code == 303

    res = client.post("/login", data={"email": "a@example.com", "password": "secret123"})
    assert res.status_code == 200
    assert "이메일 또는 비밀번호가 올바르지 않습니다" in res.text


def test_delete_account_keeps_order_history(client, seeded, login, db):
    login()
    client.post("/cart/items", data={"product_id": 1, "quantity": 1})
    order_no = (
        client.post(
            "/checkout",
            data={
                "receiver_name": "홍",
                "receiver_phone": "01012345678",
                "address": "서울",
                "payment_method": "card",
            },
            follow_redirects=False,
        )
        .headers["location"]
        .rsplit("/", 1)[-1]
    )

    client.post("/mypage/delete", data={"password": "secret123"})

    count = db.execute("SELECT COUNT(*) FROM orders WHERE order_no = ?", (order_no,)).fetchone()[0]
    assert count == 1
    row = db.execute("SELECT email, name, phone FROM users WHERE id = 1").fetchone()
    assert row["email"].startswith("deleted+1@")
    assert row["name"] == "탈퇴회원"
    assert row["phone"] is None
