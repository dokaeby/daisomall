from __future__ import annotations


def test_home_returns_200_with_empty_catalog(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "상품이 없습니다" in res.text


def test_database_file_is_created(app):
    assert app.state.db_path.exists()
