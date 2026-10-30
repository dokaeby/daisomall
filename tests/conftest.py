from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.auth.passwords import hash_password
from app.config import Settings
from app.db import connect, now_iso, transaction
from app.main import create_app
from app.repositories.products import create_product


@pytest.fixture
def app(tmp_path):
    return create_app(
        Settings(
            database_path=tmp_path / "test.db",
            admin_email="admin@test.local",
            admin_password="adminpass123",
        )
    )


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db(app):
    conn = connect(app.state.db_path)
    yield conn
    conn.close()


@pytest.fixture
def seeded(app, db):
    with transaction(db):
        create_product(
            db,
            name="주방 수세미",
            description="3개입",
            price=1000,
            category="주방",
            stock=10,
            emoji="🧽",
        )
        create_product(
            db,
            name="욕실 샴푸",
            description="500ml",
            price=3000,
            category="욕실",
            stock=5,
            emoji="🧴",
        )
    return app


@pytest.fixture
def signup(client):
    def _signup(
        email: str = "a@example.com",
        password: str = "secret123",
        name: str = "홍길동",
        phone: str = "",
    ):
        return client.post(
            "/signup",
            data={"email": email, "password": password, "name": name, "phone": phone},
            follow_redirects=False,
        )

    return _signup


@pytest.fixture
def login(client, signup):
    def _login(email: str = "a@example.com", password: str = "secret123"):
        signup(email=email, password=password)
        return client.post("/login", data={"email": email, "password": password})

    return _login


@pytest.fixture
def admin_login(app, client, db):
    def _login():
        with transaction(db):
            db.execute(
                "INSERT INTO users (email, password_hash, name, is_admin, created_at)"
                " VALUES (?, ?, ?, 1, ?) ON CONFLICT (email) DO NOTHING",
                ("admin@test.local", hash_password("adminpass123"), "관리자", now_iso()),
            )
        client.post("/login", data={"email": "admin@test.local", "password": "adminpass123"})

    return _login


@pytest.fixture
def place_order(client):
    def _place(product_id: int = 1, quantity: int = 1, payment_method: str = "card") -> str:
        client.post("/cart/items", data={"product_id": product_id, "quantity": quantity})
        res = client.post(
            "/checkout",
            data={
                "receiver_name": "홍길동",
                "receiver_phone": "01012345678",
                "address": "서울시 어딘가 1",
                "payment_method": payment_method,
            },
            follow_redirects=False,
        )
        return res.headers["location"].rsplit("/", 1)[-1]

    return _place
