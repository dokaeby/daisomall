from __future__ import annotations

from app.db import transaction
from app.repositories.products import create_product


def test_list_shows_active_products(client, seeded):
    res = client.get("/")
    assert "주방 수세미" in res.text
    assert "욕실 샴푸" in res.text


def test_search_and_category_filter(client, seeded):
    assert "주방 수세미" in client.get("/?q=수세미").text
    assert "욕실 샴푸" not in client.get("/?q=수세미").text
    assert "욕실 샴푸" in client.get("/?category=욕실").text
    assert "주방 수세미" not in client.get("/?category=욕실").text


def test_detail_and_missing_product(client, seeded):
    assert client.get("/products/1").status_code == 200
    assert client.get("/products/9999").status_code == 404


def test_inactive_products_are_hidden(client, seeded, db):
    with transaction(db):
        db.execute("UPDATE products SET is_active = 0 WHERE id = 1")
    assert "주방 수세미" not in client.get("/").text
    assert client.get("/products/1").status_code == 404


def test_pagination_shows_twelve_per_page(client, seeded, db):
    with transaction(db):
        for i in range(20):
            create_product(
                db,
                name=f"추가 상품 {i}",
                description="",
                price=1000,
                category="문구",
                stock=3,
                emoji="✏️",
            )
    first = client.get("/")
    second = client.get("/?page=2")
    assert first.text.count('class="card"') == 12
    assert second.text.count('class="card"') == 10
