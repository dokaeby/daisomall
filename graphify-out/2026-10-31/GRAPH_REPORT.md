# Graph Report - shoppingmall  (2026-10-31)

## Corpus Check
- 44 files · ~13,870 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 5 file(s) not represented in the graph (top: (none) 2, .example 1, .css 1)

## Summary
- 350 nodes · 906 edges · 21 communities (14 shown, 7 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 79 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- service.py
- main.py
- repositories/orders.py
- repositories/cart.py
- render
- 다이소형 생활용품 쇼핑몰 — 상세 기획서
- transaction
- Review Focus
- product_create
- submit_checkout
- now_iso
- order_detail
- 다이소몰 (로컬 데모)
- test_admin.py
- shoppingmall

## God Nodes (most connected - your core abstractions)
1. `transaction()` - 37 edges
2. `render()` - 32 edges
3. `now_iso()` - 17 edges
4. `User` - 16 edges
5. `connect()` - 16 edges
6. `Review Focus` - 16 edges
7. `require_user()` - 15 edges
8. `get_db()` - 15 edges
9. `hash_password()` - 14 edges
10. `checkout()` - 14 edges

## Surprising Connections (you probably didn't know these)
- `Task 6: 상품 목록/상세` --references--> `get_db()`  [INFERRED]
  docs/superpowers/plans/2026-10-31-shoppingmall.md → app/db.py
- `Review Focus` --references--> `safe_next()`  [INFERRED]
  docs/superpowers/plans/2026-10-31-shoppingmall.md → app/auth/deps.py
- `Task 10: 구매내역, 주문 상세, 배송조회` --references--> `require_user()`  [INFERRED]
  docs/superpowers/plans/2026-10-31-shoppingmall.md → app/auth/deps.py
- `Task 5: 회원탈퇴` --references--> `require_user()`  [INFERRED]
  docs/superpowers/plans/2026-10-31-shoppingmall.md → app/auth/deps.py
- `Task 7: 장바구니` --references--> `require_user()`  [INFERRED]
  docs/superpowers/plans/2026-10-31-shoppingmall.md → app/auth/deps.py

## Import Cycles
- None detected.

## Communities (21 total, 7 thin omitted)

### Community 0 - "service.py"
Cohesion: 0.15
Nodes (16): current_user_dep(), require_admin(), require_user(), current_user(), normalize_email(), pop_flash(), set_flash(), sign_in() (+8 more)

### Community 1 - "main.py"
Cohesion: 0.11
Nodes (22): _load_dotenv(), load_settings(), Settings, connect(), init_db(), create_app(), http_error_handler(), unhandled_error_handler() (+14 more)

### Community 2 - "repositories/orders.py"
Cohesion: 0.11
Nodes (25): clear_cart(), create_order(), decrement_stock(), get_order(), list_all_orders(), list_order_items(), list_orders(), mark_paid() (+17 more)

### Community 3 - "repositories/cart.py"
Cohesion: 0.12
Nodes (18): add_item(), cart_count(), CartLine, delete_item(), list_items(), update_quantity(), get_product(), list_categories() (+10 more)

### Community 4 - "render"
Cohesion: 0.11
Nodes (12): safe_next(), delete_account(), login(), login_form(), _login_response(), logout(), mypage(), signup() (+4 more)

### Community 5 - "다이소형 생활용품 쇼핑몰 — 상세 기획서"
Cohesion: 0.07
Nodes (29): 10. 실행 방법, 11. 파일 구조, 12. 빌더에게 남기는 판단, 13. Supabase 전환 계획 (1차 완료 후), 1. 의도, 2. 범위, 3. 아키텍처, 4. 데이터 모델 (SQLite) (+21 more)

### Community 6 - "transaction"
Cohesion: 0.12
Nodes (9): transaction(), create_product(), test_sold_out_product_is_not_added(), test_insufficient_stock_rolls_back_everything(), test_order_keeps_price_and_name_snapshot(), test_payment_failure_leaves_no_order_and_no_stock_change(), test_zero_stock_product_blocks_checkout(), test_inactive_products_are_hidden() (+1 more)

### Community 7 - "Review Focus"
Cohesion: 0.15
Nodes (14): hash_password(), verify_password(), AuthError, delete_account(), Review Focus, Task 12: 시드, 화면 다듬기, 실행 경로, Task 13: 실제 기동 검증, Task 2: 비밀번호 해싱 (+6 more)

### Community 8 - "product_create"
Cohesion: 0.27
Nodes (6): mark_delivered(), order_list(), product_create(), product_list(), _products_page(), register_shipping()

### Community 9 - "submit_checkout"
Cohesion: 0.30
Nodes (6): add_item(), cart_page(), checkout_page(), delete_item(), submit_checkout(), update_item()

### Community 10 - "now_iso"
Cohesion: 0.25
Nodes (7): now_iso(), create(), find_by_email(), find_by_id(), Global Constraints, 다이소형 쇼핑몰 Implementation Plan, 의존 관계

### Community 11 - "order_detail"
Cohesion: 0.39
Nodes (3): order_detail(), order_list(), _timeline()

### Community 12 - "다이소몰 (로컬 데모)"
Cohesion: 0.25
Nodes (7): 검사, 구조, 기능, 다이소몰 (로컬 데모), 보안 메모 (로컬 데모 기준), 실행, 환경변수

### Community 13 - "test_admin.py"
Cohesion: 0.38
Nodes (3): _login_as_buyer(), test_admin_registers_tracking_then_delivers(), test_shipping_requires_valid_tracking_number()

## Knowledge Gaps
- **34 isolated node(s):** `shoppingmall`, `실행`, `환경변수`, `검사`, `기능` (+29 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 110 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `transaction()` connect `transaction` to `service.py`, `main.py`, `repositories/orders.py`, `repositories/cart.py`, `Review Focus`, `product_create`, `submit_checkout`, `now_iso`?**
  _High betweenness centrality (0.146) - this node is a cross-community bridge._
- **Why does `render()` connect `render` to `service.py`, `main.py`, `repositories/cart.py`, `product_create`, `submit_checkout`, `order_detail`?**
  _High betweenness centrality (0.100) - this node is a cross-community bridge._
- **Why does `Supabase 전환` connect `service.py` to `다이소몰 (로컬 데모)`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `transaction()` (e.g. with `Task 1: 스캐폴드, 설정, DB 스키마, 홈` and `Task 3: 회원가입`) actually correct?**
  _`transaction()` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `User` (e.g. with `current_user_dep()` and `require_admin()`) actually correct?**
  _`User` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `shoppingmall`, `실행`, `환경변수` to the rest of the system?**
  _34 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1073170731707317 - nodes in this community are weakly interconnected._