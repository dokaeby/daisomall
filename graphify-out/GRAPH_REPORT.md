# Graph Report - shoppingmall  (2026-10-31)

## Corpus Check
- 48 files · ~14,909 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 2, .example 1, .css 1)

## Summary
- 363 nodes · 888 edges · 18 communities (11 shown, 7 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 79 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- service.py
- db.py
- admin.py
- products.py
- render
- 다이소형 생활용품 쇼핑몰 — 상세 기획서
- transaction
- MockPaymentGateway
- routers/cart.py
- 다이소몰 (로컬 데모)
- test_admin.py
- shoppingmall

## God Nodes (most connected - your core abstractions)
1. `transaction()` - 34 edges
2. `render()` - 31 edges
3. `now_iso()` - 17 edges
4. `Review Focus` - 16 edges
5. `hash_password()` - 14 edges
6. `connect()` - 14 edges
7. `다이소형 생활용품 쇼핑몰 — 상세 기획서` - 14 edges
8. `User` - 13 edges
9. `create_product()` - 13 edges
10. `checkout()` - 13 edges

## Surprising Connections (you probably didn't know these)
- `Global Constraints` --references--> `now_iso()`  [INFERRED]
  docs/superpowers/plans/2026-10-31-shoppingmall.md → app/db.py
- `Review Focus` --references--> `safe_next()`  [INFERRED]
  docs/superpowers/plans/2026-10-31-shoppingmall.md → app/auth/deps.py
- `Task 10: 구매내역, 주문 상세, 배송조회` --references--> `require_user()`  [INFERRED]
  docs/superpowers/plans/2026-10-31-shoppingmall.md → app/auth/deps.py
- `Task 7: 장바구니` --references--> `require_user()`  [INFERRED]
  docs/superpowers/plans/2026-10-31-shoppingmall.md → app/auth/deps.py
- `Task 11: 관리자 (상품 등록, 운송장, 배송완료)` --references--> `require_admin()`  [INFERRED]
  docs/superpowers/plans/2026-10-31-shoppingmall.md → app/auth/deps.py

## Import Cycles
- None detected.

## Communities (18 total, 7 thin omitted)

### Community 0 - "service.py"
Cohesion: 0.10
Nodes (32): current_user_dep(), require_admin(), require_user(), hash_password(), verify_password(), AuthError, current_user(), delete_account() (+24 more)

### Community 1 - "db.py"
Cohesion: 0.09
Nodes (18): _load_dotenv(), load_settings(), Settings, connect(), connect_postgres(), _db_type(), init_db(), _schema_sql() (+10 more)

### Community 2 - "admin.py"
Cohesion: 0.09
Nodes (24): set_flash(), flash_redirect(), timeline_steps(), create_order(), get_order(), list_all_orders(), list_order_items(), list_orders() (+16 more)

### Community 3 - "products.py"
Cohesion: 0.15
Nodes (17): now_iso(), add_item(), cart_count(), CartLine, delete_item(), list_items(), update_quantity(), get_product() (+9 more)

### Community 4 - "render"
Cohesion: 0.12
Nodes (12): safe_next(), delete_account(), login(), login_form(), _login_response(), logout(), mypage(), signup() (+4 more)

### Community 5 - "다이소형 생활용품 쇼핑몰 — 상세 기획서"
Cohesion: 0.07
Nodes (29): 10. 실행 방법, 11. 파일 구조, 12. 빌더에게 남기는 판단, 13. Supabase 전환 계획 (1차 완료 후), 1. 의도, 2. 범위, 3. 아키텍처, 4. 데이터 모델 (SQLite) (+21 more)

### Community 6 - "transaction"
Cohesion: 0.07
Nodes (21): transaction(), create_product(), Global Constraints, 다이소형 쇼핑몰 Implementation Plan, 의존 관계, admin_login(), _login(), client() (+13 more)

### Community 7 - "MockPaymentGateway"
Cohesion: 0.31
Nodes (5): MockPaymentGateway, PaymentResult, test_charge_fails_over_limit(), test_charge_succeeds_at_or_under_limit(), test_unknown_method_fails()

### Community 9 - "routers/cart.py"
Cohesion: 0.12
Nodes (18): clear_cart(), decrement_stock(), mark_paid(), add_item(), cart_page(), checkout_page(), delete_item(), submit_checkout() (+10 more)

### Community 12 - "다이소몰 (로컬 데모)"
Cohesion: 0.25
Nodes (7): 검사, 구조, 기능, 다이소몰 (로컬 데모), 보안 메모 (로컬 데모 기준), 실행, 환경변수

### Community 13 - "test_admin.py"
Cohesion: 0.38
Nodes (3): _login_as_buyer(), test_admin_registers_tracking_then_delivers(), test_shipping_requires_valid_tracking_number()

## Knowledge Gaps
- **34 isolated node(s):** `shoppingmall`, `실행`, `환경변수`, `검사`, `기능` (+29 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 118 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `transaction()` connect `transaction` to `service.py`, `db.py`, `admin.py`, `routers/cart.py`?**
  _High betweenness centrality (0.148) - this node is a cross-community bridge._
- **Why does `render()` connect `render` to `service.py`, `db.py`, `admin.py`, `products.py`, `routers/cart.py`?**
  _High betweenness centrality (0.114) - this node is a cross-community bridge._
- **Why does `Supabase 전환` connect `service.py` to `다이소몰 (로컬 데모)`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `transaction()` (e.g. with `Task 1: 스캐폴드, 설정, DB 스키마, 홈` and `Task 3: 회원가입`) actually correct?**
  _`transaction()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Review Focus` (e.g. with `safe_next()` and `current_user()`) actually correct?**
  _`Review Focus` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `hash_password()` (e.g. with `Task 12: 시드, 화면 다듬기, 실행 경로` and `Task 2: 비밀번호 해싱`) actually correct?**
  _`hash_password()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `shoppingmall`, `실행`, `환경변수` to the rest of the system?**
  _34 weakly-connected nodes found - possible documentation gaps or missing edges._