# 다이소형 생활용품 쇼핑몰 — 상세 기획서

- 작성일: 2026-10-31
- 상태: 승인 대기
- 스택: Python 3.13 / FastAPI / Jinja2 / SQLite / 순수 HTML+CSS
- 실행 환경: 로컬 전용 (Supabase는 1차 완료 후 연동)

## 1. 의도

다품종 소량 생필품을 파는 쇼핑몰을, 회원이 가입부터 배송조회까지 끊김 없이 쓸 수 있는
최소 완결 형태로 만든다. 화려한 기능이 아니라 **주문이 실제로 성립하고, 그 기록이
나중에 조회 가능한 것**이 목표다.

성공 기준: 로컬에서 서버를 띄우고 브라우저로 가입 → 상품 탐색 → 장바구니 → 결제 →
구매내역 → 배송조회 → 탈퇴까지 한 번에 통과한다. 테스트 스위트가 이 흐름을 자동으로
검증한다.

## 2. 범위

### 목표 (v1 포함)

| # | 기능 | 설명 |
|---|------|------|
| F1 | 회원가입 | 이메일/비밀번호/이름/휴대폰. 이메일 중복 거부, 비밀번호 정책 검사 |
| F2 | 로그인/로그아웃 | 세션 쿠키 발급/폐기. 로그인 상태 유지 |
| F3 | 인증 | 보호 페이지 접근 제어, 비로그인 시 로그인 페이지로 리다이렉트 후 원래 경로 복귀 |
| F4 | 회원탈퇴 | 비밀번호 재확인 후 소프트 삭제. 개인정보 마스킹, 세션 전부 폐기, 주문 기록은 보존 |
| F5 | 상품 목록 | 카테고리 필터, 이름 검색, 페이지네이션, 품절/판매중지 표시 |
| F6 | 상품 상세 | 가격·설명·재고·카테고리, 수량 선택 후 장바구니 담기 |
| F7 | 장바구니 | 추가/수량 변경/삭제, 합계 금액, 재고 초과 방지, 품목 1개당 1행 |
| F8 | 결제 | 배송지 입력 → 주문 생성 → 모의 결제 → 재고 차감. 실패 시 주문 미확정 |
| F9 | 구매내역 | 본인 주문만 목록/상세 조회, 상태·금액·품목 스냅샷 표시 |
| F10 | 배송조회 | 주문 상태 타임라인 + 택배사/운송장번호 조회 |
| F11 | 관리자 | 상품 등록, 운송장 등록(출고 처리). 일반 회원 접근 차단 |

### 비목표 (v1 제외, 필요해지면 별도 승인)

- 실제 PG 결제 연동(토스페이먼츠 등) — 사업자·계약 선행 필요
- 택배사 배송조회 API 연동 — 운송장 번호와 상태값만 저장
- 리뷰·평점, 찜, 쿠폰, 포인트, 추천, 재입고 알림
- 상품 이미지 업로드/스토리지 — 상품당 이모지 1개로 대체
- 주문 취소/환불/교환 워크플로
- 다국어, 이메일 발송(가입 확인·비밀번호 재설정), 소셜 로그인
- 실시간 재고 동시성 제어(비관적 락, 큐) — 로컬 단일 프로세스 가정

### 안티골 (이렇게 되면 실패)

- 결제는 성공했다는데 재고/주문이 안 맞는다
- 남의 주문이 조회된다
- 비밀번호가 평문 또는 복호화 가능한 형태로 남는다
- 탈퇴한 회원이 계속 로그인된다

## 3. 아키텍처

```
browser ──HTTP──> FastAPI (Jinja2 SSR)
                     │
                     ├─ routers/        화면 라우트 (HTML 응답)
                     ├─ services/      주문·장바구니·인증 도메인 로직
                     ├─ repositories/  SQLite 접근 (파라미터 바인딩만)
                     ├─ db.py          연결/스키마/마이그레이션
                     └─ templates/ + static/style.css
```

- SSR만 사용. JSON API 없음. 폼 제출 + 303 Redirect(GET) 패턴으로 새로고침 중복 제출 방지.
- 도메인 로직은 `services/`에 두어 라우트와 분리한다(테스트 대상).
- DB 접근은 `repositories/`에 모아 SQL을 한 곳에 격리한다.
- Jinja2 autoescape 기본 ON.

### 인증 경계 (Supabase 대비)

인증은 `auth/` 모듈 하나로 캡슐화한다. 라우터는 아래 인터페이스만 안다.

```python
sign_up(email, password, name, phone) -> user_id
sign_in(email, password) -> session_token
sign_out(session_token) -> None
current_user(session_token) -> User | None
delete_account(user_id, password) -> None
```

- **v1 구현체**: `LocalAuth` — `users` 테이블 + scrypt 해시 + `sessions` 테이블.
- **Supabase 전환 시**: `SupabaseAuth` 구현체로 교체. Supabase가 비밀번호/세션을 소유하고,
  FastAPI는 Supabase JWT(Authorization 또는 쿠키)를 검증한 뒤 `users.supabase_uid`로
  로컬 프로필을 매핑한다. 라우터·템플릿은 수정하지 않는다.
- 두 구현체를 동시에 유지하지 않는다. 지금 `SupabaseAuth` 코드는 쓰지 않는다(검증 불가).

## 4. 데이터 모델

**SQLite:** `AUTOINCREMENT`, `executescript()`, `PRAGMA foreign_keys`.
**PostgreSQL:** `SERIAL`, `psycopg3` `dict_row`, `RETURNING id`.
Schema is the same logical model; DDL differences are in `schema.py` (`SCHEMA_SQL` / `SCHEMA_SQL_POSTGRES`).

금액은 원 단위 정수. 시각은 ISO8601 UTC 문자열.

금액은 원 단위 정수. 시각은 ISO8601 UTC 문자열.

### users
| 컬럼 | 타입 | 제약 |
|------|------|------|
| id | INTEGER | PK AUTOINCREMENT |
| email | TEXT | NOT NULL, UNIQUE (저장 시 소문자 정규화) |
| password_hash | TEXT | NOT NULL (`scrypt$n$r$p$salt$hash`) |
| name | TEXT | NOT NULL |
| phone | TEXT | NULL |
| is_admin | INTEGER | NOT NULL DEFAULT 0 |
| supabase_uid | TEXT | NULL, UNIQUE — 전환용 자리 |
| created_at | TEXT | NOT NULL |
| deleted_at | TEXT | NULL — 소프트 삭제 |

탈퇴 시: `deleted_at` 기록, `email`을 `deleted+{id}@invalid.local`로 치환,
`password_hash`를 무작위 값으로 덮어쓰기, `name`/`phone` 마스킹. 주문 FK는 유지.

### sessions
| 컬럼 | 타입 | 제약 |
|------|------|------|
| token | TEXT | PK (secrets.token_urlsafe(32)) |
| user_id | INTEGER | NOT NULL FK users(id) |
| created_at | TEXT | NOT NULL |
| expires_at | TEXT | NOT NULL (발급 +7일) |

### products
| 컬럼 | 타입 | 제약 |
|------|------|------|
| id | INTEGER | PK |
| name | TEXT | NOT NULL |
| description | TEXT | NOT NULL DEFAULT '' |
| price | INTEGER | NOT NULL, CHECK(price >= 0) |
| category | TEXT | NOT NULL |
| stock | INTEGER | NOT NULL, CHECK(stock >= 0) |
| emoji | TEXT | NOT NULL DEFAULT '📦' |
| is_active | INTEGER | NOT NULL DEFAULT 1 |
| created_at | TEXT | NOT NULL |

### cart_items
`id PK / user_id FK / product_id FK / quantity INTEGER CHECK(quantity>0) / added_at`
`UNIQUE(user_id, product_id)`

### orders
`id PK / order_no TEXT UNIQUE / user_id FK / status TEXT / total_amount INTEGER /
receiver_name TEXT / receiver_phone TEXT / address TEXT / payment_method TEXT /
paid_at TEXT NULL / carrier TEXT NULL / tracking_no TEXT NULL / created_at TEXT`

- status: `PENDING` → `PAID` → `PREPARING` → `SHIPPED` → `DELIVERED`, 예외 `CANCELLED`
- order_no: `YYYYMMDD-{4자리 일련번호}` (해당 일자 최대값 + 1, 트랜잭션 내 계산)

### order_items
`id PK / order_id FK / product_id FK / product_name TEXT / unit_price INTEGER / quantity INTEGER`

- `product_name`, `unit_price`는 **주문 시점 스냅샷**. 이후 상품명/가격이 바뀌어도 내역은 불변.

## 5. 화면과 라우트

| 메서드 | 경로 | 인증 | 설명 |
|--------|------|------|------|
| GET | `/` | - | 상품 목록 (`q`, `category`, `page`) |
| GET | `/products/{id}` | - | 상품 상세. 판매중지/없음 → 404 |
| GET/POST | `/signup` | - | 가입 폼/처리 |
| GET/POST | `/login` | - | 로그인 폼/처리 (`next` 지원) |
| POST | `/logout` | 필요 | 세션 폐기 후 `/` |
| GET | `/cart` | 필요 | 장바구니 |
| POST | `/cart/items` | 필요 | 담기 (`product_id`, `quantity`) |
| POST | `/cart/items/{id}` | 필요 | 수량 변경 (`quantity`) |
| POST | `/cart/items/{id}/delete` | 필요 | 삭제 |
| GET | `/checkout` | 필요 | 배송지 입력 + 주문 요약 |
| POST | `/checkout` | 필요 | 주문 생성 + 모의 결제 |
| GET | `/orders` | 필요 | 구매내역 |
| GET | `/orders/{order_no}` | 필요 | 주문 상세 + 배송조회 |
| GET | `/mypage` | 필요 | 회원 정보 |
| POST | `/mypage/delete` | 필요 | 탈퇴 (`password` 재확인) |
| GET | `/admin/products` | 관리자 | 상품 목록/등록 폼 |
| POST | `/admin/products` | 관리자 | 상품 등록 |
| POST | `/admin/orders/{order_no}/shipping` | 관리자 | 운송장 등록 → SHIPPED |
| POST | `/admin/orders/{order_no}/delivered` | 관리자 | 배송완료 처리 → DELIVERED |

공통 레이아웃: 상단 내비게이션(상품·장바구니(개수)·구매내역·마이페이지·로그인/로그아웃),
flash 메시지 영역, 푸터. CSS는 `static/style.css` 한 파일, 반응형 그리드.

목록 기본값: 판매중 상품만, 최신 등록순, 페이지당 12개. 카테고리 목록은 DB의 활성 상품에서
distinct로 뽑아 별도 테이블을 두지 않는다.

## 6. 핵심 동작 규칙

### 가입/로그인
- 이메일 형식 검사(간단한 정규식), 소문자 정규화, 공백 제거.
- 비밀번호: 8자 이상 72자 이하. (scrypt 입력 제한)
- 이름 1~50자, 휴대폰은 선택이며 숫자/하이픈 10~13자.
- 중복 이메일(탈퇴 포함) → "이미 사용 중인 이메일입니다".
- 로그인 실패는 이메일 존재 여부를 구분하지 않는다(계정 열거 방지).
- `next` 파라미터는 **내부 경로(`/`로 시작, `//` 제외)만** 허용. 오픈 리다이렉트 차단.

### 장바구니
- 같은 상품 재추가 시 수량 합산(행 추가 아님).
- 수량은 1 이상, 재고 이하. 초과 시 현재 재고로 클램프하고 경고 메시지.
- 비활성/삭제 상품은 장바구니에서 제외하고 "판매 종료" 표시.

### 결제 (모의)
1. 장바구니가 비었으면 400 + 장바구니로 리다이렉트.
2. 배송지(받는 사람/연락처/주소) 검증.
3. 단일 트랜잭션:
   - 각 품목 재고 확인. 부족하면 전체 롤백 후 재고 부족 메시지.
   - `orders`(PENDING) + `order_items`(가격·이름 스냅샷) 생성.
   - 모의 결제 호출. 성공 시 재고 차감, `PAID`, `paid_at` 기록, 장바구니 비우기.
   - 실패 시 롤백(주문 자체를 남기지 않음), 실패 메시지.
4. 성공 → `303 /orders/{order_no}`.
- 모의 결제 규칙: `total_amount > 1_000_000` 이면 실패(한도 초과), 그 외 성공.
  결제 수단은 `card` / `bank_transfer` 라디오 버튼.

### 배송조회
- 상태 타임라인: 결제완료 → 상품준비중 → 배송중 → 배송완료. 현재 단계 강조.
- 운송장 등록 전에는 "운송장 정보 없음" 표시.
- 관리자가 운송장 등록 시 `SHIPPED` + `carrier`/`tracking_no` 저장.
- 관리자가 배송완료 처리 시 `DELIVERED`. `SHIPPED` 상태에서만 허용.
- `PREPARING`은 v1에서 전이 경로가 없다(결제 직후 `PAID`). 타임라인은 현재 상태까지만 채운다.

### 관리자
- `is_admin=1` 계정만 접근. 비관리자는 403.
- 관리자 계정은 시드 스크립트로만 생성(`ADMIN_EMAIL`/`ADMIN_PASSWORD` 환경변수).

## 7. 보안

| 항목 | 처리 |
|------|------|
| 비밀번호 | `hashlib.scrypt` (n=2^14, r=8, p=1) + 사용자별 16바이트 salt, `hmac.compare_digest` 비교 |
| 세션 | 256비트 랜덤 토큰, httpOnly + SameSite=Lax + (운영 시) Secure, 7일 만료 |
| CSRF | SameSite=Lax 쿠키 + 상태 변경은 POST 전용. 운영 배포 시 CSRF 토큰 추가 필요 |
| SQL injection | 전 구간 파라미터 바인딩, 문자열 조합 금지 |
| XSS | Jinja2 autoescape, `|safe` 사용 금지 |
| 접근 제어 | 모든 소유 리소스는 `WHERE user_id = ?`로 조회. 남의 주문/장바구니는 404 |
| 로그 | 이메일·토큰·비밀번호는 로그에 남기지 않는다 |
| 오픈 리다이렉트 | `next` 화이트리스트 규칙 |
| 비밀값 | `.env`에서 로드, `.gitignore` 등록, `.env.example`만 커밋 |

## 8. 오류 처리

- 검증 실패: 폼 재표시 + 필드별 메시지, 200 (PRG 위반 아님)
- 404: 없는 상품/주문 → 커스텀 404 템플릿
- 403: 관리자 페이지 비권한
- 500: `logger.exception` 기록 후 일반 오류 템플릿(내부 정보 미노출)
- DB 오류는 잡아서 로깅 후 500. 조용히 삼키지 않는다.

## 9. 테스트 전략 (TDD)

- `pytest` + `fastapi.testclient.TestClient`, 테스트마다 임시 SQLite 파일/인메모리 DB.
- SQLite 기본: 현재 54개 테스트 모든 통과. `DATABASE_TYPE=postgres`로 테스트 대상 변경 가능.
- 라우트가 아닌 서비스 계층부터 테스트를 먼저 작성한다.
- 필수 케이스:

| 영역 | 케이스 |
|------|--------|
| auth | 가입 성공/중복/약한 비밀번호/이메일 형식, 로그인 성공·실패, 로그아웃, 세션 만료, 보호 페이지 리다이렉트, `next` 오픈 리다이렉트 차단, 탈퇴 후 로그인 불가 |
| products | 목록/검색/카테고리/페이지네이션, 비활성 상품 404 |
| cart | 추가/중복 합산/수량 변경/삭제, 재고 초과 클램프, 타 사용자 장바구니 접근 차단 |
| checkout | 빈 장바구니 거부, 정상 주문(스냅샷·재고 차감·장바구니 비움), 재고 부족 롤백, 결제 실패 시 주문 미생성 |
| orders | 본인 주문만 조회, 타인 주문 404, 상태 표시 |
| admin | 비관리자 403, 상품 등록, 운송장 등록 → SHIPPED |
| payments | 한도 초과 실패, 정상 성공 |

- 회귀 방지: 위 케이스는 구현과 함께 커밋되어 `pytest`로 상시 실행.
- 실행: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`

## 10. 실행 방법

```bash
uv sync
uv run python -m app.seed          # 관리자 1명 + 상품 24종
uv run uvicorn app.main:app --reload --port 8000
```

`.env.example`: `DATABASE_TYPE` (기본 `sqlite`), `DATABASE_PATH`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `SESSION_DAYS`(기본 7).
세션은 서명 쿠키가 아니라 DB 토큰이므로 `SECRET_KEY`가 필요 없다.

## 11. 파일 구조

```
app/
  main.py            앱 생성, 미들웨어, 예외 핸들러
  config.py          환경변수 로딩
  db.py              연결, 스키마 초기화
  auth/__init__.py   인증 경계 (LocalAuth)
  repositories/      users, products, cart, orders
  services/          cart_service, order_service, payment
  routers/           public, auth, cart, orders, admin
  templates/         layout, index, product_detail, signup, login, cart,
                     checkout, orders, order_detail, mypage, admin_*, 404, 500
  static/style.css
  seed.py
tests/
  conftest.py, test_auth.py, test_products.py, test_cart.py,
  test_checkout.py, test_orders.py, test_admin.py, test_payment.py
```

## 12. 빌더에게 남기는 판단

- 상품 이미지 대신 이모지 사용: 이미지 자산·업로드가 범위 밖이라.
- 관리자 화면은 등록/운송장 두 기능만. 상품 수정·삭제 UI는 만들지 않는다(시드와 SQL로 충분).
- 가입 확인 이메일 없음: 로컬 단계에서 SMTP 의존을 만들지 않기 위해.
- 주문 상태 전이는 관리자 운송장 등록과 결제만 존재. `PREPARING`/`DELIVERED` 수동 변경 UI는 v1에서 생략.

## 13. Supabase 전환 계획 (1차 완료 후)

1. Supabase 프로젝트 생성, Email/Password 인증 활성화.
2. `users.supabase_uid` 마이그레이션, `LocalAuth` → `SupabaseAuth` 교체.
3. Supabase JWT 검증(`SUPABASE_JWT_SECRET` 또는 JWKS), 쿠키 대신 Supabase 세션 사용.
4. `sessions` 테이블은 사용 중지(삭제는 별도 판단).
5. 기존 로컬 계정은 이전하지 않는다(로컬은 데모 데이터). 필요 시 별도 스크립트.
