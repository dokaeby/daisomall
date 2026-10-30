# 다이소형 쇼핑몰 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 로컬에서 가입→상품탐색→장바구니→모의결제→구매내역→배송조회→탈퇴가 끊김 없이 동작하는 FastAPI/SQLite SSR 쇼핑몰을 만든다.

**Architecture:** FastAPI가 Jinja2로 HTML을 렌더링한다. 도메인 로직은 `app/services/`, SQL은 `app/repositories/`, 인증은 `app/auth/` 한 모듈에 격리해 나중에 Supabase 구현체로 교체한다. SQLite는 요청당 연결 1개, 쓰기는 명시적 `transaction()` 컨텍스트로 묶는다.

**Tech Stack:** Python 3.13, FastAPI, Jinja2, SQLite(stdlib), pytest, ruff, pyright. 패키지 관리: uv.

**Spec:** `docs/superpowers/specs/2026-10-31-daisomall-design.md`

## Global Constraints

- 금액은 원 단위 `int`. DB에 float 금액 없음.
- 비밀번호는 `hashlib.scrypt`(n=16384, r=8, p=1) + 16바이트 salt, 저장 형식 `scrypt$16384$8$1$<salt_hex>$<hash_hex>`.
- 세션 토큰은 `secrets.token_urlsafe(32)`, 쿠키 이름 `sid`, `httponly=True`, `samesite="lax"`, 만료 7일(설정 가능).
- 모든 SQL은 파라미터 바인딩. 문자열 포맷으로 SQL 조립 금지.
- Jinja2 autoescape 유지, `|safe` 금지.
- 리소스 조회는 항상 `user_id` 조건 포함. 남의 리소스는 404.
- 상태 변경은 POST만. 성공 후 `303` 리다이렉트(PRG).
- 시각은 UTC ISO8601 문자열(`db.now_iso()`).
- 커밋은 사용자 요청 시에만 한다(AGENTS.md). 이 계획의 각 태스크는 커밋하지 않고 테스트 통과로 끝난다.
- 사용자에게 보이는 문구는 한국어.

## Review Focus

1. 동시에 같은 상품을 결제해 재고가 음수가 되는 경우 → 재고 차감은 `UPDATE ... SET stock = stock - ? WHERE id = ? AND stock >= ?`로 원자화, 영향 행 0이면 전체 롤백.
2. `next=//evil.com`, `next=/\evil.com` 같은 값 → 외부 리다이렉트. `safe_next()`가 `/`로 시작하고 `//`가 아닌 경로만 허용.
3. 장바구니 수량으로 `-1`, `0`, `10**9` 제출 → 음수 합계·재고 초과. 수량은 `max(1, min(q, stock))`로 클램프.
4. `/orders/20261031-0001`처럼 남의 주문번호 추측 → 주문 상세는 `WHERE order_no = ? AND user_id = ?`.
5. 탈퇴한 회원의 기존 세션 쿠키 재사용 → 탈퇴 시 해당 user의 세션 전부 DELETE, `current_user()`는 `deleted_at IS NULL` 조건 포함.

---

### Task 1: 스캐폴드, 설정, DB 스키마, 홈

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `.env.example`
- Create: `app/__init__.py`, `app/config.py`, `app/db.py`, `app/main.py`, `app/web.py`
- Create: `app/templates/layout.html`, `app/templates/index.html`
- Create: `app/static/style.css`
- Test: `tests/conftest.py`, `tests/test_app.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `app/config.py`: `@dataclass(frozen=True) class Settings: database_path: Path; database_type: str = "sqlite"; admin_email: str; admin_password: str; session_days: int = = 7`, `load_settings() -> Settings`
  - `app/db.py`: `SCHEMA_SQL: str`, `SCHEMA_SQL_POSTGRES: str`, `connect(path: Path) -> sqlite3.Connection`, `connect_postgres(url: str) -> object`, `init_db(path: Path | str, database_type: str = "sqlite") -> None`, `get_db(request: Request) -> Iterator[object]`, `transaction(conn: object) -> Iterator[object]` (contextmanager), `now_iso() -> str`, `_should_use_postgres() -> bool`
  - `app/main.py`: `create_app(settings: Settings) -> FastAPI`, `app`
  - `app/web.py`: `templates: Jinja2Templates`, `render(request, conn, name: str, **context) -> HTMLResponse`
  - `create_app`은 `app.state.settings`와 `app.state.db_path`를 노출한다.

- [ ] **Step 1: 프로젝트 파일 작성**

`pyproject.toml`:

```toml
[project]
name = "daisomall"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["fastapi>=0.115", "uvicorn[standard]>=0.32", "jinja2>=3.1", "python-multipart>=0.0.12"]

[dependency-groups]
dev = ["pytest>=8.3", "httpx>=0.28", "ruff>=0.8", "pyright>=1.1.390"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"

pythonpath = ["."]

[tool.pyright]
include = ["app", "tests"]
venvPath = "."
venv = ".venv"
pythonVersion = "3.12"
typeCheckingMode = "basic"
```

`.gitignore`: `.venv/`, `__pycache__/`, `*.db`, `.env`, `.pytest_cache/`, `.ruff_cache/`, `.pytest_cache/`

`.env.example`: `DATABASE_TYPE=sqlite`, `DATABASE_PATH=./shop.db`, `ADMIN_EMAIL=admin@example.com`, `ADMIN_PASSWORD=change-me-please`, `SESSION_DAYS=7`

- [ ] **Step 2: 스키마와 연결 코드 작성**

`app/db.py`의 `SCHEMA_SQL`은 스펙 4장의 6개 테이블(`users`, `sessions`, `products`, `cart_items`, `orders`, `order_items`)을 그대로 담는다. `sessions`에는 `flash TEXT` 컬럼을 추가한다(플래시 메시지 저장, 서명 쿠키 의존성 제거). `PRAGMA foreign_keys=ON`은 `connect()`에서 실행한다. `connect()`는 `isolation_level=None`(자동커밋 모드)으로 열고 `row_factory=sqlite3.Row`를 설정한다.

`transaction()`은 `BEGIN IMMEDIATE` → yield → `COMMIT`, 예외 시 `ROLLBACK` 후 재발생.

- [ ] **Step 3: 실패하는 테스트 작성**

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app


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
    return TestClient(app)


# tests/test_app.py
def test_home_returns_200_with_empty_catalog(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "상품이 없습니다" in res.text


def test_database_file_is_created(app):
    assert app.state.db_path.exists()
```

- [ ] **Step 4: 테스트 실패 확인**

Run: `uv run pytest tests/test_app.py -v`
Expected: FAIL (`app.main` 없음 또는 `create_app` 미정의)

- [ ] **Step 5: `config.py`, `web.py`, `main.py`, 최소 템플릿/CSS 구현**

`create_app`은 시작 시 `init_db`, `/static` 마운트, `templates` 연결, 404/500 예외 핸들러 등록을 한다. 홈 라우트는 Task 6에서 상품 목록으로 채우고, 지금은 빈 목록을 넘긴다.

- [ ] **Step 6: 테스트 통과 확인**

Run: `uv run pytest tests/test_app.py -v`
Expected: 2 passed

---

### Task 2: 비밀번호 해싱

**Files:**
- Create: `app/auth/__init__.py`, `app/auth/passwords.py`
- Test: `tests/test_passwords.py`

**Interfaces:**
- Consumes: 없음
- Produces: `hash_password(password: str) -> str`, `verify_password(password: str, stored: str) -> bool`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
from app.auth.passwords import hash_password, verify_password


def test_hash_is_salted_and_verifiable():
    a, b = hash_password("secret123"), hash_password("secret123")
    assert a != b
    assert a.startswith("scrypt$16384$8$1$")
    assert verify_password("secret123", a) and verify_password("secret123", b)


def test_wrong_password_and_malformed_hash_are_rejected():
    assert not verify_password("nope", hash_password("secret123"))
    assert not verify_password("secret123", "garbage")
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/test_passwords.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: 구현**

`hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)`. 비교는 `hmac.compare_digest`. 저장 문자열 파싱 실패 시 `False` 반환. 비밀번호 72자 초과는 `ValueError`를 던지지 않고 앞 72자를 쓰지 않는다 — 대신 `hash_password`에서 `ValueError("비밀번호는 72자 이하여야 합니다")`를 던지고, 호출부(가입 검증)가 먼저 길이를 검사한다.

- [ ] **Step 4: 통과 확인**

Run: `uv run pytest tests/test_passwords.py -v`
Expected: 2 passed

---

### Task 3: 회원가입

**Files:**
- Create: `app/auth/service.py`, `app/repositories/users.py`
- Create: `app/routers/auth.py`, `app/templates/signup.html`
- Modify: `app/main.py` (라우터 등록)
- Test: `tests/test_signup.py`

**Interfaces:**
- Consumes: `hash_password`, `db.get_db`, `db.transaction`
- Produces:
  - `app/auth/service.py`: `@dataclass(frozen=True) class User: id: int; email: str; name: str; phone: str | None; is_admin: bool`, `class AuthError(Exception)` (`.message: str`), `sign_up(conn, *, email: str, password: str, name: str, phone: str | None) -> int`
  - `app/repositories/users.py`: `find_by_email(conn, email: str) -> sqlite3.Row | None`, `find_by_id(conn, user_id: int) -> sqlite3.Row | None`, `create(conn, *, email: str, password_hash: str, name: str, phone: str | None) -> int`
  - 라우트: `GET/POST /signup`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
def test_signup_creates_account_and_redirects(client):
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


def test_signup_rejects_duplicate_email_case_insensitively(client):
    data = {"email": "a@example.com", "password": "secret123", "name": "홍", "phone": ""}
    client.post("/signup", data=data)
    res = client.post("/signup", data={**data, "email": "A@EXAMPLE.COM"})
    assert res.status_code == 200
    assert "이미 사용 중인 이메일" in res.text


def test_signup_rejects_short_password_and_bad_email(client):
    res = client.post(
        "/signup", data={"email": "not-an-email", "password": "short", "name": "홍", "phone": ""}
    )
    assert res.status_code == 200
    assert "이메일 형식" in res.text and "8자 이상" in res.text
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/test_signup.py -v`
Expected: 3 failed (404)

- [ ] **Step 3: 구현**

이메일은 `strip().lower()`, 검증 정규식 `^[^@\s]+@[^@\s]+\.[^@\s]+$`. 중복 검사는 `deleted_at` 포함 전체에서 수행(탈퇴 이메일은 치환되므로 실제 충돌 없음). 검증 오류는 `AuthError`를 모아 한 번에, 템플릿에 `error: str`로 전달. 성공 시 `sign_in()`으로 세션을 만들어 `303 /`로 보낸다(자동 로그인).

```python
assert res.headers["location"] == "/login"
```

- [ ] **Step 4: 통과 확인**

Run: `uv run pytest tests/test_signup.py -v`
Expected: 3 passed

---

### Task 4: 로그인/로그아웃/세션/접근 제어

**Files:**
- Modify: `app/auth/service.py` (`sign_in`, `sign_out`, `current_user`, `set_flash`, `pop_flash`)
- Create: `app/auth/deps.py`
- Modify: `app/routers/auth.py`, `app/templates/layout.html`
- Create: `app/templates/login.html`
- Test: `tests/test_login.py`

**Interfaces:**
- Consumes: Task 3의 `User`, `find_by_email`
- Produces:
  - `app/auth/service.py`: `sign_in(conn, *, email: str, password: str) -> str` (토큰, 실패 시 `AuthError("이메일 또는 비밀번호가 올바르지 않습니다")`), `sign_out(conn, token: str) -> None`, `current_user(conn, token: str | None) -> User | None`, `set_flash(conn, token: str, message: str) -> None`, `pop_flash(conn, token: str | None) -> str | None`
  - `app/auth/deps.py`: `SESSION_COOKIE = "sid"`, `safe_next(value: str | None) -> str` (허용 안 되면 `"/"`), `current_user_dep(request, conn=Depends(get_db)) -> User | None`, `require_user(...) -> User`, `require_admin(...) -> User`
  - `require_user`는 비로그인 시 `HTTPException(303, headers={"Location": f"/login?next={quote(path)}"})`
  - `require_admin`은 비관리자 시 `HTTPException(403)`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
def test_login_sets_cookie_and_redirects_to_next(client):
    client.post(
        "/signup",
        data={"email": "a@example.com", "password": "secret123", "name": "홍", "phone": ""},
    )
    res = client.post(
        "/login?next=/cart",
        data={"email": "a@example.com", "password": "secret123"},
        follow_redirects=False,
    )
    assert res.status_code == 303 and res.headers["location"] == "/cart"
    assert "sid" in res.cookies


def test_login_failure_is_generic(client):
    res = client.post("/login", data={"email": "ghost@example.com", "password": "x"})
    assert "이메일 또는 비밀번호가 올바르지 않습니다" in res.text


def test_protected_page_redirects_anonymous_to_login(client):
    res = client.get("/cart", follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"].startswith("/login?next=%2Fcart")


def test_logout_clears_session(client):
    client.post(
        "/signup",
        data={"email": "a@example.com", "password": "secret123", "name": "홍", "phone": ""},
    )
    client.post("/login", data={"email": "a@example.com", "password": "secret123"})
    client.post("/logout")
    assert client.get("/cart", follow_redirects=False).status_code == 303


@pytest.mark.parametrize(
    "bad", ["//evil.com", "/\\evil.com", "http://evil.com", "javascript:alert(1)"]
)
def test_safe_next_rejects_external(bad):
    from app.auth.deps import safe_next

    assert safe_next(bad) == "/"


def test_safe_next_accepts_internal_path():
    from app.auth.deps import safe_next

    assert safe_next("/orders/20261031-0001") == "/orders/20261031-0001"
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/test_login.py -v`
Expected: FAIL

- [ ] **Step 3: 구현**

쿠키 설정은 `response.set_cookie("sid", token, httponly=True, samesite="lax", max_age=settings.session_days*86400, path="/")`. 로그아웃은 DB 세션 삭제 + `delete_cookie`. `current_user`는 `sessions.expires_at > now` 및 `users.deleted_at IS NULL` 조건. 만료 세션은 조회 시 삭제한다.

- [ ] **Step 4: 통과 확인**

Run: `uv run pytest tests/test_login.py -v`
Expected: 7 passed

---

### Task 5: 회원탈퇴

**Files:**
- Modify: `app/auth/service.py` (`delete_account`), `app/routers/auth.py`, `app/templates/mypage.html`
- Modify: `app/main.py` (마이페이지 라우트 등록)
- Test: `tests/test_delete_account.py`

**Interfaces:**
- Consumes: `verify_password`, `require_user`
- Produces: `delete_account(conn, *, user_id: int, password: str) -> None` — 실패 시 `AuthError("비밀번호가 올바르지 않습니다")`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
def _signup_and_login(client, email="a@example.com"):
    client.post(
        "/signup", data={"email": email, "password": "secret123", "name": "홍", "phone": ""}
    )
    client.post("/login", data={"email": email, "password": "secret123"})


def test_delete_account_requires_correct_password(client):
    _signup_and_login(client)
    res = client.post("/mypage/delete", data={"password": "wrong"})
    assert "비밀번호가 올바르지 않습니다" in res.text
    assert client.get("/mypage", follow_redirects=False).status_code == 200


def test_delete_account_removes_sessions_and_blocks_login(client):
    _signup_and_login(client)
    token = client.cookies["sid"]
    client.post("/mypage/delete", data={"password": "secret123"})
    assert client.get("/mypage", follow_redirects=False).status_code == 303
    res = client.post("/login", data={"email": "a@example.com", "password": "secret123"})
    assert res.status_code == 200 and "이메일 또는 비밀번호" in res.text
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/test_delete_account.py -v`
Expected: FAIL (404)

- [ ] **Step 3: 구현**

한 트랜잭션에서: `users.deleted_at=now`, `email=deleted+{id}@invalid.local`, `password_hash=hash_password(secrets.token_hex(16))`, `name='탈퇴회원'`, `phone=NULL`, `sessions` 전부 삭제. 주문/주문상품은 건드리지 않는다. 성공 후 `/`로 303.

- [ ] **Step 4: 통과 확인**

Run: `uv run pytest tests/test_delete_account.py -v`
Expected: 2 passed

---

### Task 6: 상품 목록/상세

**Files:**
- Create: `app/repositories/products.py`, `app/routers/shop.py`, `app/templates/product_detail.html`
- Modify: `app/templates/index.html`, `app/main.py`
- Test: `tests/test_products.py`

**Interfaces:**
- Consumes: `get_db`
- Produces:
  - `@dataclass(frozen=True) class Product: id: int; name: str; description: str; price: int; category: str; stock: int; emoji: str; is_active: bool`
  - `list_products(conn, *, q: str | None = None, category: str | None = None, page: int = 1, per_page: int = 12) -> tuple[list[Product], int]`
  - `get_product(conn, product_id: int) -> Product | None` (비활성 포함, 라우트에서 필터)
  - `list_categories(conn) -> list[str]`
  - `create_product(conn, *, name: str, description: str, price: int, category: str, stock: int, emoji: str) -> int`
  - 라우트: `GET /`, `GET /products/{product_id}`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
import pytest
from app.db import connect, init_db, transaction, _should_use_postgres
from app.repositories.products import create_product


@pytest.fixture
def seeded(app):
    conn = connect(app.state.db_path)
    with transaction(conn):
        create_product(
            conn,
            name="주방 수세미",
            description="3개입",
            price=1000,
            category="주방",
            stock=10,
            emoji="🧽",
        )
        create_product(
            conn,
            name="욕실 샴푸",
            description="500ml",
            price=3000,
            category="욕실",
            stock=5,
            emoji="🧴",
        )
    conn.close()
    return app


def test_list_shows_only_active_products(client, seeded):
    res = client.get("/")
    assert "주방 수세미" in res.text and "욕실 샴푸" in res.text


def test_search_and_category_filter(client, seeded):
    assert "주방 수세미" in client.get("/?q=수세미").text
    assert "욕실 샴푸" not in client.get("/?q=수세미").text
    assert "욕실 샴푸" in client.get("/?category=욕실").text
    assert "주방 수세미" not in client.get("/?category=욕실").text


def test_detail_and_missing_product(client, seeded):
    assert client.get("/products/1").status_code == 200
    assert client.get("/products/9999").status_code == 404
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/test_products.py -v`
Expected: FAIL

- [ ] **Step 3: 구현**

목록 SQL은 `is_active=1` 고정, `q`는 `name LIKE '%' || ? || '%'`, 정렬 `id DESC`, `LIMIT ? OFFSET ?`. 전체 개수는 같은 조건의 `COUNT(*)`. 페이지는 1 미만이면 1로 보정. 상세가 없거나 `is_active=0`이면 404 템플릿.

- [ ] **Step 4: 통과 확인**

Run: `uv run pytest tests/test_products.py -v`
Expected: 3 passed

---

### Task 7: 장바구니

**Files:**
- Create: `app/repositories/cart.py`, `app/services/cart_service.py`, `app/routers/cart.py`
- Create: `app/templates/cart.html`
- Modify: `app/main.py`, `app/templates/layout.html` (장바구니 뱃지)
- Test: `tests/test_cart.py`

**Interfaces:**
- Consumes: `Product`, `get_product`, `require_user`
- Produces:
  - `@dataclass(frozen=True) class CartLine: id: int; product: Product; quantity: int` + `subtotal: int` property
  - `app/repositories/cart.py`: `add_item(conn, user_id: int, product_id: int, quantity: int) -> None`, `list_items(conn, user_id: int) -> list[CartLine]`, `update_quantity(conn, user_id: int, item_id: int, quantity: int) -> bool`, `delete_item(conn, user_id: int, item_id: int) -> None`, `clear_cart(conn, user_id: int) -> None`, `cart_count(conn, user_id: int) -> int`
  - `app/services/cart_service.py`: `add_to_cart(conn, user_id: int, product_id: int, quantity: int) -> str` (사용자에게 보여줄 메시지), `change_quantity(conn, user_id: int, item_id: int, quantity: int) -> None`
  - 라우트: `GET /cart`, `POST /cart/items`, `POST /cart/items/{item_id}`, `POST /cart/items/{item_id}/delete`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
def _login(client):
    client.post(
        "/signup",
        data={"email": "a@example.com", "password": "secret123", "name": "홍", "phone": ""},
    )
    client.post("/login", data={"email": "a@example.com", "password": "secret123"})


def test_add_item_and_duplicate_merges_quantity(client, seeded):
    _login(client)
    client.post("/cart/items", data={"product_id": 1, "quantity": 2})
    client.post("/cart/items", data={"product_id": 1, "quantity": 3})
    res = client.get("/cart")
    assert res.text.count("주방 수세미") == 1
    assert "5,000원" in res.text


def test_quantity_is_clamped_to_stock(client, seeded):
    _login(client)
    client.post("/cart/items", data={"product_id": 1, "quantity": 999})
    assert "10" in client.get("/cart").text  # 재고 10으로 클램프


def test_zero_or_negative_quantity_is_clamped_to_one(client, seeded):
    _login(client)
    client.post("/cart/items", data={"product_id": 1, "quantity": 0})
    assert "1,000원" in client.get("/cart").text


def test_update_and_delete_item(client, seeded):
    _login(client)
    client.post("/cart/items", data={"product_id": 1, "quantity": 1})
    client.post("/cart/items/1", data={"quantity": 4})
    assert "4,000원" in client.get("/cart").text
    client.post("/cart/items/1/delete")
    assert "장바구니가 비어 있습니다" in client.get("/cart").text


def test_cannot_touch_other_users_cart(client, seeded):
    _login(client)
    client.post("/cart/items", data={"product_id": 1, "quantity": 1})
    client.post("/logout")
    client.post(
        "/signup",
        data={"email": "b@example.com", "password": "secret123", "name": "김", "phone": ""},
    )
    client.post("/login", data={"email": "b@example.com", "password": "secret123"})
    client.post("/cart/items/1/delete")
    client.post("/cart/items/1", data={"quantity": 3})
    assert "4,000원" in client.get("/cart").text
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/test_cart.py -v`
Expected: FAIL

- [ ] **Step 3: 구현**

`add_to_cart`는 `quantity = max(1, min(quantity, product.stock))`. 재고 0이면 `"품절 상품입니다"` 반환하고 아무것도 넣지 않는다. 기존 행이 있으면 `quantity = min(기존+추가, stock)`. `list_items`는 비활성 상품도 반환하되 템플릿에서 "판매 종료" 표시(합계 제외). `cart_count`는 `SUM(quantity)`.

- [ ] **Step 4: 통과 확인**

Run: `uv run pytest tests/test_cart.py -v`
Expected: 5 passed

---

### Task 8: 모의 결제 게이트웨이

**Files:**
- Create: `app/services/payment.py`
- Test: `tests/test_payment.py`

**Interfaces:**
- Produces: `@dataclass(frozen=True) class PaymentResult: ok: bool; message: str`, `class MockPaymentGateway: limit: int = 1_000_000; def charge(self, amount: int, method: str) -> PaymentResult`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
from app.services.payment import MockPaymentGateway


def test_charge_succeeds_under_limit():
    assert MockPaymentGateway().charge(999_999, "card").ok
    assert MockPaymentGateway().charge(1_000_000, "bank_transfer").ok


def test_charge_fails_over_limit():
    r = MockPaymentGateway().charge(1_000_001, "card")
    assert not r.ok and "한도" in r.message


def test_unknown_method_fails():
    r = MockPaymentGateway().charge(1000, "crypto")
    assert not r.ok and "결제 수단" in r.message
```

- [ ] **Step 2: 실패 확인** → `uv run pytest tests/test_payment.py -v` → FAIL
- [ ] **Step 3: 구현** (성공 메시지 `"결제가 완료되었습니다"`)
- [ ] **Step 4: 통과 확인** → 3 passed

---

### Task 9: 주문 생성 (체크아웃)

**Files:**
- Create: `app/repositories/orders.py`, `app/services/checkout.py`
- Modify: `app/routers/cart.py` (`GET/POST /checkout`), `app/main.py`
- Create: `app/templates/checkout.html`
- Test: `tests/test_checkout.py`

**Interfaces:**
- Consumes: `CartLine`, `MockPaymentGateway`, `transaction`
- Produces:
  - `@dataclass(frozen=True) class OrderItem: product_id: int; product_name: str; unit_price: int; quantity: int` + `subtotal` property
  - `@dataclass(frozen=True) class Order: id: int; order_no: str; status: str; total_amount: int; receiver_name: str; receiver_phone: str; address: str; payment_method: str; paid_at: str | None; carrier: str | None; tracking_no: str | None; created_at: str`
  - `app/repositories/orders.py`: `create_order(conn, *, user_id: int, lines: list[CartLine], receiver_name: str, receiver_phone: str, address: str, payment_method: str) -> str` (order_no 반환, `PENDING`), `get_order(conn, order_no: str, user_id: int | None = None) -> Order | None`, `list_orders(conn, user_id: int) -> list[Order]`, `list_order_items(conn, order_id: int) -> list[OrderItem]`, `mark_paid(conn, order_id: int) -> None`, `decrement_stock(conn, product_id: int, quantity: int) -> bool`, `set_shipped(conn, order_no: str, carrier: str, tracking_no: str) -> bool`, `set_delivered(conn, order_no: str) -> bool`
  - `app/services/checkout.py`: `class CheckoutError(Exception)` (`.message: str`), `checkout(conn, user_id: int, *, receiver_name: str, receiver_phone: str, address: str, payment_method: str, gateway: MockPaymentGateway | None = None) -> str`
  - 라우트: `GET /checkout`, `POST /checkout`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
def test_checkout_creates_paid_order_snapshots_and_decrements_stock(client, seeded):
    _login(client)
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
    assert "결제완료" in detail.text and "2,000원" in detail.text
    assert "장바구니가 비어 있습니다" in client.get("/cart").text


def test_checkout_with_empty_cart_is_rejected(client, seeded):
    _login(client)
    res = client.post(
        "/checkout",
        data={
            "receiver_name": "홍",
            "receiver_phone": "010",
            "address": "서울",
            "payment_method": "card",
        },
        follow_redirects=False,
    )
    assert res.status_code == 303 and res.headers["location"] == "/cart"


def test_insufficient_stock_rolls_back_everything(client, seeded):
    _login(client)
    client.post("/cart/items", data={"product_id": 1, "quantity": 10})
    with connect(client.app.state.db_path) as conn:  # 재고를 결제 직전에 줄여 경합 재현
        with transaction(conn):
            conn.execute("UPDATE products SET stock = 1 WHERE id = 1")
    res = client.post(
        "/checkout",
        data={
            "receiver_name": "홍",
            "receiver_phone": "010",
            "address": "서울",
            "payment_method": "card",
        },
    )
    assert "재고" in res.text
    with connect(client.app.state.db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0


def test_payment_failure_keeps_no_order_and_no_stock_change(client, seeded):
    _login(client)
    client.post("/cart/items", data={"product_id": 2, "quantity": 1})
    with connect(client.app.state.db_path) as conn:
        with transaction(conn):
            conn.execute("UPDATE products SET price = 2000000 WHERE id = 2")
    res = client.post(
        "/checkout",
        data={
            "receiver_name": "홍",
            "receiver_phone": "010",
            "address": "서울",
            "payment_method": "card",
        },
    )
    assert "한도" in res.text
    with connect(client.app.state.db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
        assert conn.execute("SELECT stock FROM products WHERE id = 2").fetchone()[0] == 5
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/test_checkout.py -v`
Expected: FAIL

- [ ] **Step 3: 구현**

`checkout()` 순서: 전체를 하나의 `transaction()`으로 감싼다.
1. `list_items`로 활성 상품만 추린다. 비었으면 `CheckoutError("장바구니가 비어 있습니다")`.
2. 배송지 3개 필드 검증(빈 값 거부, 연락처는 숫자·하이픈 10~13자).
3. `create_order` → `PENDING` 주문 + 스냅샷 품목 생성, order_no는 `YYYYMMDD-` + 당일 최대 일련번호+1 4자리.
4. `gateway.charge(total, method)` 호출. 실패하면 `CheckoutError(result.message)` → 롤백.
5. 각 품목 `decrement_stock`; 하나라도 `False`면 `CheckoutError("재고가 부족한 상품이 있습니다: {이름}")` → 롤백.
6. `mark_paid`, `clear_cart`, 커밋.
라우트는 `CheckoutError`를 잡아 체크아웃 템플릿에 `error`로 표시(200), 빈 장바구니만 303 `/cart`.

- [ ] **Step 4: 통과 확인**

Run: `uv run pytest tests/test_checkout.py -v`
Expected: 4 passed

---

### Task 10: 구매내역, 주문 상세, 배송조회

**Files:**
- Modify: `app/routers/cart.py` → `app/routers/orders.py`로 분리, `app/main.py`
- Create: `app/templates/orders.html`, `app/templates/order_detail.html`
- Test: `tests/test_orders.py`

**Interfaces:**
- Consumes: `list_orders`, `get_order`, `list_order_items`, `require_user`
- Produces: 라우트 `GET /orders`, `GET /orders/{order_no}`. 템플릿 컨텍스트: `order`, `items`, `timeline: list[tuple[str, str, bool]]` (`(상태코드, 라벨, 도달여부)`)

- [ ] **Step 1: 실패하는 테스트 작성**

```python
def test_orders_only_show_my_orders(client, seeded):
    _login(client)
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
    client.post("/logout")
    client.post(
        "/signup",
        data={"email": "b@example.com", "password": "secret123", "name": "김", "phone": ""},
    )
    client.post("/login", data={"email": "b@example.com", "password": "secret123"})
    assert "주문 내역이 없습니다" in client.get("/orders").text
    assert client.get(f"/orders/{order_no}").status_code == 404


def test_order_detail_shows_timeline_and_no_tracking_number(client, seeded):
    _login(client)
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
    res = client.get(f"/orders/{order_no}")
    assert "결제완료" in res.text and "운송장 정보 없음" in res.text
```

- [ ] **Step 2: 실패 확인** → `uv run pytest tests/test_orders.py -v` → FAIL
- [ ] **Step 3: 구현**

타임라인 매핑: `PAID`→결제완료, `PREPARING`→상품준비중, `SHIPPED`→배송중, `DELIVERED`→배송완료. 현재 상태 인덱스까지 `True`. `CANCELLED`는 별도 배지. 운송장이 없으면 "운송장 정보 없음".

- [ ] **Step 4: 통과 확인** → 2 passed

---

### Task 11: 관리자 (상품 등록, 운송장, 배송완료)

**Files:**
- Create: `app/routers/admin.py`, `app/templates/admin_products.html`, `app/templates/admin_orders.html`
- Modify: `app/main.py`, `app/repositories/orders.py` (`set_shipped`, `set_delivered` 이미 정의됨)
- Test: `tests/test_admin.py`

**Interfaces:**
- Consumes: `require_admin`, `create_product`, `list_products`, `set_shipped`, `set_delivered`, `get_order`
- Produces: 라우트 `GET /admin/products`, `POST /admin/products`, `GET /admin/orders`, `POST /admin/orders/{order_no}/shipping`, `POST /admin/orders/{order_no}/delivered`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
def _login_admin(client, app):
    with connect(app.state.db_path) as conn, transaction(conn):
        conn.execute(
            "INSERT INTO users (email, password_hash, name, is_admin, created_at) VALUES (?,?,?,1,?)",
            ("admin@test.local", hash_password("adminpass123"), "관리자", now_iso()),
        )
    client.post("/login", data={"email": "admin@test.local", "password": "adminpass123"})


def test_non_admin_gets_403(client, seeded):
    _login(client)
    assert client.get("/admin/products").status_code == 403


def test_admin_creates_product_and_it_appears_in_list(client, seeded, app):
    _login_admin(client, app)
    client.post(
        "/admin/products",
        data={
            "name": "새 상품",
            "description": "설명",
            "price": "1500",
            "category": "생활",
            "stock": "7",
            "emoji": "🧦",
        },
    )
    assert "새 상품" in client.get("/").text


def test_admin_registers_tracking_then_delivers(client, seeded, app):
    _login(client)
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
    client.post("/logout")
    _login_admin(client, app)
    client.post(
        f"/admin/orders/{order_no}/shipping",
        data={"carrier": "CJ대한통운", "tracking_no": "1234567890"},
    )
    res = client.get(f"/orders/{order_no}")
    assert "배송중" in res.text and "1234567890" in res.text
    client.post(f"/admin/orders/{order_no}/delivered")
    assert "배송완료" in client.get(f"/orders/{order_no}").text
```

- [ ] **Step 2: 실패 확인** → `uv run pytest tests/test_admin.py -v` → FAIL
- [ ] **Step 3: 구현**

`set_shipped`는 `UPDATE orders SET status='SHIPPED', carrier=?, tracking_no=? WHERE order_no=? AND status IN ('PAID','PREPARING')`, `set_delivered`는 `... WHERE order_no=? AND status='SHIPPED'`. 영향 행 0이면 400 + 메시지.

- [ ] **Step 4: 통과 확인** → 3 passed

---

### Task 12: 시드, 화면 다듬기, 실행 경로

**Files:**
- Create: `app/seed.py`, `README.md`
- Modify: `app/templates/layout.html`, `app/templates/index.html`, `app/static/style.css`
- Test: `tests/test_seed.py`

**Interfaces:**
- Consumes: `create_product`, `hash_password`
- Produces: `seed(settings: Settings) -> None` (멱등: 관리자 이메일이 있으면 건너뛰고, 상품이 0개일 때만 24종 삽입)

- [ ] **Step 1: 실패하는 테스트 작성**

```python
def test_seed_is_idempotent(app):
    from app.seed import seed

    seed(app.state.settings)
    seed(app.state.settings)
    with connect(app.state.db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 24
        assert conn.execute("SELECT COUNT(*) FROM users WHERE is_admin=1").fetchone()[0] == 1
```

- [ ] **Step 2: 실패 확인** → FAIL
- [ ] **Step 3: 구현**

상품 24종은 6개 카테고리(주방/욕실/문구/청소/수납/패션) × 4종, 가격 500~5,000원. README에 실행 3줄과 환경변수 표.

- [ ] **Step 4: 통과 확인** → 1 passed
- [ ] **Step 5: 전체 검사**

Run: `uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run pyright`
Expected: 전부 통과

---

### Task 13: 실제 기동 검증

- [ ] **Step 1: 서버 기동**

```bash
uv run python -m app.seed
uv run uvicorn app.main:app --port 8000
```

- [ ] **Step 2: 브라우저 수동 시나리오**

가입 → 로그인 → 카테고리 필터 → 상품 상세 → 장바구니 2종 → 100만원 초과 결제 실패 확인 → 정상 결제 → 구매내역 → 상세 배송조회 → 관리자 운송장 등록 → 배송중 확인 → 배송완료 → 로그아웃 → 탈퇴 → 재로그인 실패.

- [ ] **Step 3: 결과 기록**

각 단계 통과/실패를 보고서에 적는다. 실패 시 재현 테스트를 먼저 추가하고 고친다.

---

## 의존 관계

Task 1 → 2 → 3 → 4 → 5, 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13.
Task 6은 3·4와 독립이지만 로그인 뱃지 때문에 4 이후가 안전하다.
