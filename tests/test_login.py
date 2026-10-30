from __future__ import annotations

import pytest

from app.auth.deps import safe_next


def test_login_sets_cookie_and_redirects_to_next(client, signup):
    signup()
    res = client.post(
        "/login",
        data={"email": "a@example.com", "password": "secret123", "next": "/cart"},
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert res.headers["location"] == "/cart"
    assert "sid" in res.cookies


def test_login_failure_is_generic(client):
    res = client.post("/login", data={"email": "ghost@example.com", "password": "x"})
    assert res.status_code == 200
    assert "이메일 또는 비밀번호가 올바르지 않습니다" in res.text


def test_protected_page_redirects_anonymous_to_login(client):
    res = client.get("/cart", follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == "/login?next=%2Fcart"


def test_logout_clears_session(client, login):
    login()
    assert client.get("/mypage").status_code == 200
    client.post("/logout")
    assert client.get("/mypage", follow_redirects=False).status_code == 303


@pytest.mark.parametrize(
    "bad",
    [
        "//evil.com",
        "/\\evil.com",
        "http://evil.com",
        "javascript:alert(1)",
        "/\t/evil.com",
        "",
        None,
    ],
)
def test_safe_next_rejects_external(bad):
    assert safe_next(bad) == "/"


def test_safe_next_accepts_internal_path():
    assert safe_next("/orders/20261031-0001") == "/orders/20261031-0001"
