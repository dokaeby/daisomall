# 다이소몰 (Local Demo)

A multi-category, small-quantity daily necessities shop. FastAPI + Jinja2 SSR + SQLite / PostgreSQL.

- Design spec: `docs/superpowers/specs/2026-10-31-daisomall-design.md`
- Implementation plan: `docs/superpowers/plans/2026-10-31-daisomall.md`

## Run

```bash
uv sync
cp .env.example .env          # adjust values
uv run python -m app.seed     # 1 admin + 24 products (idempotent)
uv run uvicorn app.asgi:app --reload --port 8000
```

- Admin credentials: `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env` (defaults `admin@example.com` / `change-me-please`)
- Regular users: sign up at `/signup`. Automatically logged in after registration.

## Environment Variables

| Name | Default | Description |
|------|---------|-------------|
| `DATABASE_TYPE` | `sqlite` | Database engine: `sqlite` or `postgres` |
| `DATABASE_PATH` | `./shop.db` | SQLite file path **or** PostgreSQL connection URL (e.g. `postgresql://user:pass@localhost/shop`) |
| `ADMIN_EMAIL` | `admin@example.com` | Seed admin email |
| `ADMIN_PASSWORD` | `change-me-please` | Seed admin password |
| `SESSION_DAYS` | `7` | Session validity (days) |

`.env` is git-ignored.

## Checks

```bash
uv run pytest                  # 54 tests
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

## Features

Sign-up · Login/Logout · Session auth · Account deletion (masking, orders preserved) ·
Product listing/search/category/pagination · Product detail · Shopping cart ·
Mock payment (fails >1,000,000 KRW) · Purchase history · Shipping tracking (status timeline + tracking number) ·
Admin (product registration, tracking registration, delivery complete).

## Project Structure

```
app/
  main.py          App factory, route/exception handler registration
  asgi.py          Uvicorn entry point
  config.py        Environment variable loading
  db.py            Connection routing, transactions, schema init  ← SQLite / PostgreSQL switch
  schema.py        Dual DDL constants (SCHEMA_SQL, SCHEMA_SQL_POSTGRES)
  auth/            passwords, service, deps   ← Supabase swap point
  repositories/    users, products, cart, orders
  services/        payment(mock), cart_service, checkout
  routers/         shop, auth, cart, orders, admin
  templates/       Jinja2
  static/style.css
  seed.py
tests/             54 tests
```

## Database Switch (SQLite ↔ PostgreSQL)

Set `DATABASE_TYPE=postgres` and point `DATABASE_PATH` to a valid PostgreSQL connection URL
(e.g. `postgresql://user:pass@localhost/shop`). The app automatically uses `psycopg3` with
`row_factory=dict_row`. DDL differences (`AUTOINCREMENT` vs `SERIAL`) are handled internally.
Default remains SQLite for local development.

## Supabase 전환 (Future)

`app/auth/`의 함수 시그니처(`sign_up`, `sign_in`, `sign_out`, `current_user`,
`delete_account`)를 유지한 채 구현체를 `SupabaseAuth`로 교체한다. 라우터와 템플릿은
수정하지 않는다. `users.supabase_uid` 컬럼은 미리 준비되어 있다.

## Security Notes (Local Demo)

- Passwords: `scrypt` + per-user salt, compared via `hmac.compare_digest`.
- Sessions: 256-bit random token, `httpOnly` + `SameSite=Lax` cookie. Stored in DB; revoked on logout/deletion.
- CSRF: `SameSite=Lax` only on state-changing POST. **Add CSRF tokens for production.**
- Cookie `Secure` flag is off for local HTTP. Enable it in production.
- Payment is a mock gateway. Real PG integration is pluggable via `app/services/payment.py`.
