from __future__ import annotations


def test_signup_creates_account_and_logs_in(client):
    res = client.post(
        "/signup",
        data={
            "email": "A@Example.com",
            "password": "secret123",
            "name": "홍길동",
            "phone": "010-1234-5678",
        },
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert res.headers["location"] == "/"
    assert "sid" in res.cookies


def test_signup_rejects_duplicate_email_case_insensitively(client, signup):
    signup(email="a@example.com")
    res = signup(email="A@EXAMPLE.COM")
    assert res.status_code == 200
    assert "이미 사용 중인 이메일" in res.text


def test_signup_rejects_short_password_and_bad_email(client):
    res = client.post(
        "/signup",
        data={"email": "not-an-email", "password": "short", "name": "홍", "phone": ""},
    )
    assert res.status_code == 200
    assert "이메일 형식" in res.text
    assert "8자 이상" in res.text


def test_signup_rejects_bad_phone(client):
    res = client.post(
        "/signup",
        data={"email": "a@example.com", "password": "secret123", "name": "홍", "phone": "abc"},
    )
    assert res.status_code == 200
    assert "연락처" in res.text
