from __future__ import annotations


def _login_as_buyer(client):
    client.post("/login", data={"email": "a@example.com", "password": "secret123"})


def test_non_admin_gets_403(client, seeded, login):
    login()
    assert client.get("/admin/products").status_code == 403
    assert client.get("/admin/orders").status_code == 403


def test_admin_creates_product_and_it_appears_in_list(client, seeded, admin_login):
    admin_login()
    res = client.post(
        "/admin/products",
        data={
            "name": "새 상품",
            "description": "설명",
            "price": "1500",
            "category": "생활",
            "stock": "7",
            "emoji": "🧦",
        },
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert "새 상품" in client.get("/").text


def test_admin_product_form_rejects_invalid_values(client, seeded, admin_login):
    admin_login()
    res = client.post(
        "/admin/products",
        data={
            "name": "",
            "description": "",
            "price": "-1",
            "category": "",
            "stock": "x",
            "emoji": "",
        },
    )
    assert res.status_code == 200
    assert "가격" in res.text
    assert "재고" in res.text


def test_admin_registers_tracking_then_delivers(client, seeded, login, admin_login, place_order):
    login()
    order_no = place_order()
    client.post("/logout")

    admin_login()
    client.post(
        f"/admin/orders/{order_no}/shipping",
        data={"carrier": "CJ대한통운", "tracking_no": "1234567890"},
    )
    client.post("/logout")
    _login_as_buyer(client)

    detail = client.get(f"/orders/{order_no}")
    assert "현재 상태: 배송중" in detail.text
    assert "1234567890" in detail.text

    client.post("/logout")
    admin_login()
    client.post(f"/admin/orders/{order_no}/delivered")
    client.post("/logout")
    _login_as_buyer(client)

    assert "현재 상태: 배송완료" in client.get(f"/orders/{order_no}").text


def test_shipping_requires_valid_tracking_number(client, seeded, login, admin_login, place_order):
    login()
    order_no = place_order()
    client.post("/logout")

    admin_login()
    client.post(f"/admin/orders/{order_no}/shipping", data={"carrier": "", "tracking_no": ""})
    client.post("/logout")
    _login_as_buyer(client)

    assert "현재 상태: 결제완료" in client.get(f"/orders/{order_no}").text
