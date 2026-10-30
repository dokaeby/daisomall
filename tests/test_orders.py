from __future__ import annotations


def test_orders_only_show_my_orders(client, seeded, login, signup, place_order):
    login()
    order_no = place_order()
    client.post("/logout")
    signup(email="b@example.com", name="김철수")

    assert "주문 내역이 없습니다" in client.get("/orders").text
    assert client.get(f"/orders/{order_no}").status_code == 404


def test_order_detail_shows_timeline_and_no_tracking_number(client, seeded, login, place_order):
    login()
    order_no = place_order()
    res = client.get(f"/orders/{order_no}")
    assert "현재 상태: 결제완료" in res.text
    assert "운송장 정보 없음" in res.text


def test_orders_are_listed_with_status(client, seeded, login, place_order):
    login()
    place_order()
    res = client.get("/orders")
    assert "결제완료" in res.text
    assert "주문번호" in res.text
