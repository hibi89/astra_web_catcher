# Architecture — Astra Web Catcher (2026-10-18)

## 1. 전체 구성과 데이터 흐름

`browser HTML/CSS/JS` → `fetch /api/* + SameSite HttpOnly session cookie` → `FastAPI/Pydantic` → `sqlite3 / WAL / foreign_keys=ON` → `data/app.db`. 서버는 HTML·정적 JS/CSS와 API를 동일 origin에서 제공합니다. 두 서비스는 하나의 User/Session 테이블만 공유하고 상품·주문과 공고·지원 도메인은 분리했습니다. 상태를 브라우저 배열에 가짜로 저장하지 않습니다.

## 2. DB 테이블 및 관계

- `users`: username unique, salted PBKDF2 password_hash. `sessions`: token **SHA-256 해시만** 저장, user FK, 만료 시각.
- `categories` 1:N `products`: price·stock은 원화 정수, `CHECK >= 0`; `cart_items` (`user_id`,`product_id`) UNIQUE, 수량 `CHECK > 0`.
- `orders` (`user_id`,`request_key`) UNIQUE, `order_items`: 주문 당시 도서 제목(`title_snapshot`)과 단가(`unit_price`) 별도 저장. 주문 가격 변동 방지.
- `companies` 1:N `job_postings`: `min_years`, nullable `max_years`, `career_any` 및 `is_closed`. `bookmarks`와 `applications`는 각각 (`user_id`,`job_id`) UNIQUE.
- 실 데이터 분리: `migrations/001_initial.sql` 스키마, `app/db.py` 가상 데이터 seed. 기본 DB `data/app.db`, 테스트 DB `tmp_path/test_only.db`.

## 3. API

| 영역 | 메서드 및 경로 | 권한 |
| --- | --- | --- |
| 인증 | `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` | 로그인/로그아웃 공개, me 로그인 |
| 도서 | `GET /api/shop/categories`, `GET /api/shop/products`, `GET /api/shop/products/{id}` | 공개 |
| 장바구니 | `GET, POST /api/shop/cart`; `PATCH, DELETE /api/shop/cart/{product_id}` | 로그인 |
| 주문 | `POST, GET /api/shop/orders`; `GET /api/shop/orders/{order_id}` | 로그인 |
| 공고 | `GET /api/jobs/meta`, `GET /api/jobs/postings`, `GET /api/jobs/postings/{id}` | 공개 |
| 관심 | `POST, DELETE /api/jobs/postings/{id}/bookmark`; `GET /api/jobs/postings/{id}/status` | 로그인 |
| 지원 | `POST /api/jobs/postings/{id}/apply`, `GET /api/jobs/me`, `GET /api/jobs/applications/{id}` | 로그인 |
| 기타 | `GET /api/health`, `GET /docs` | 공개·로컬 |

모든 쓰기 본문은 Pydantic strict/extra-forbid validation으로 검증합니다. 누락·잘못된 입력은 422, 미인증은 401, 타 사용자 리소스는 404, 재고 부족·중복 지원·마감·빈 장바구니는 409를 반환합니다.

## 4. 인증과 접근 권한

로그인 시 crypto-random 세션 토큰을 생성하고 DB에는 SHA-256 해시만 저장합니다. 클라이언트에는 HttpOnly, SameSite=Lax 쿠키를 보냅니다(로컬 HTTP이므로 Secure 기본 false; HTTPS면 환경변수로 true). 모든 보호 API는 세션 쿠키 해시로 DB의 사용자 ID와 만료를 검증합니다. `user_id` 클라이언트 입력은 `extra='forbid'`로 거부하고 모든 조회·변경 SQL은 `WHERE user_id=server_session_user`로 제한합니다. 다른 사용자의 주문·지원 상세는 404를 반환합니다. 브라우저 쓰기 요청에 Origin 헤더가 있으면 동일 origin과 비교합니다. 운영용 CSRF 강화(모든 클라이언트 및 프록시 구성에 대한 검증)는 후속 과제입니다.

## 5. 주문의 정확성

1. `BEGIN IMMEDIATE`로 하나의 SQLite writer를 확보합니다.
2. `(user_id,request_key)`가 이미 있으면 **동일 주문 ID를 200**으로 반환합니다. 새 주문 생성 때는 201.
3. 장바구니와 **DB 상품 가격**을 재조회하여 합계를 서버에서 산출합니다.
4. `UPDATE products SET stock=stock-quantity WHERE stock >= quantity`를 모든 항목에 적용하며 영향을 받은 행이 하나도 없으면 전체 롤백합니다.
5. 주문·스냅샷 아이템 생성·장바구니 삭제·COMMIT까지 한 트랜잭션입니다. UNIQUE 요청 키가 DB에서도 중복 삽입을 막습니다.
6. 동시 사용자 주문은 SQLite write-lock에 직렬화되어 재고 1개에는 한 명만 성공합니다. 재고·주문·카트 불일치는 발생하지 않아야 합니다(병렬 HTTP 테스트 검증).

## 6. 지원·관심 공고

관심 등록 `INSERT OR IGNORE`와 UNIQUE 제약으로 멱등 처리합니다. 지원은 `BEGIN IMMEDIATE`, 마감 상태 확인, 기존 지원 확인 후 `INSERT`합니다. `(user_id,job_id)` UNIQUE와 409를 적용합니다. `note`는 2~1000자 길이 및 공백 문자열을 서버에서 거절합니다. 이력서 파일/기업 알림/실 지원은 없습니다.

## 7. URL 필터 정의

도서 `/shop?q=파이썬&category=1&sort=price_asc&page=2` — 검색 대상 `title`/`author` 부분일치, 가격 정렬 `id,price_asc,price_desc`, 페이지 크기 8. 채용 `/jobs?q=개발&role=백엔드&region=서울&experience=3&open_only=true&page=1` — SQL AND 결합, 입력 `experience`는 **후보자 본인의 경력 연수**; `career_any=1` 또는 `min_years <= input <= max_years` (max null은 상한 없음)만 반환. UI의 검색 변경은 page를 제거해 초기화, 페이지 버튼은 기존 필터를 보존합니다.

## 8. 관찰과 독립 설계의 구분

- **공개 페이지에서 직접 텍스트 확인:** 2026-10-18 YES24 메인 페이지의 국내도서 카테고리, 검색, 카트, 주문내역 링크(https://www.yes24.com/Main/default.aspx). 로그인/주문 동작은 시연하지 않았습니다.
- **직접 확인 못한 부분:** 원티드 메인 https://www.wanted.co.kr/ 는 페이지 열람이 도구 오류로 실패해 화면 조작·필터·지원 동작은 미관찰입니다.
- **자체 설계:** 로그인 방식, 상품·공고 필드, 필터 의미, 가격/재고 트랜잭션, 화면 구조, 샘플 전부. 실제 서비스 내부 API·코드를 추출하거나 우회하지 않았습니다.

## 9. 제한 / 운영 전 준비

SQLite 단일 writer는 소규모 로컬 데모에 적합합니다. 다중 서버 운영에서는 PostgreSQL + 서버 세션 저장소·트랜잭션 부하 테스트로 전환해야 합니다. 추가 필요 사항: CSRF 방어 강화, 계정 관리, 사용자 비밀번호 정책, rate limit, 로깅/관측, 마이그레이션 버전 관리, 백업/복구·권한 분리, TLS, 보안 헤더, 운영 동시성 테스트, 실제 Chromium E2E, 접근성 개선. 디자인 모사는 의도적으로 하지 않았습니다.

## 10. p4 소유자 API → 클라이언트 렌더링 Chart/Table

- 기존 `GET /preview`는 owner-scoped SQLite 결과를 서버 렌더링해 제공한다. 신규 `GET /client-preview`는 행 값을 HTML에 넣지 않고 owner, dataset, 예상 row count/hash, 명시적 field binding만 메타데이터로 제공한다.
- 브라우저는 same-origin `GET /client-assets/owner-client-chart-table.js`를 로드하고, HttpOnly 세션 쿠키와 함께 `GET /api/demo/series`를 호출한다. API는 쿠키에서 서버가 결정한 owner로 공유 in-memory SQLite를 조회한다.
- 클라이언트는 owner/dataset/binding/approval flags, row shape, 날짜·수치, 중복 key, count와 canonical JSON SHA-256을 검증한다. 검증 전에는 표/차트를 비우며, 빈 응답·네트워크 오류·불일치 상태를 별도로 표시한다.
- 요청 sequence 번호가 최신 요청만 화면에 반영한다. 이전 요청 응답은 버리고, 같은 이벤트 턴의 중복 호출은 합친다. 재시도는 오류 뒤 별도 API 호출로 복구한다.
- SVG/표 값은 DOM 생성과 `textContent`로만 출력한다. CSP는 script 및 API 연결을 같은 출처로 제한한다. CSS overflow 컨테이너로 좁은 화면의 표를 유지한다.
- 합성 owner A/B 데이터 격리와 API response mismatch는 실제 loopback Chromium에서 검증했다. 이 구조는 synthetic proof일 뿐이며 API/HTML의 같은 출처가 동시에 변조되는 공격을 막는 서명 구조가 아니다. 인증 발급, real owner DB, 의미 승인, generation/deployment는 여전히 차단되어 있다.

신규 모듈: `astra_contracts/owner_client_chart_table.js`; 엔드포인트 팩토리 확장: `astra_contracts/synthetic_owner_isolation.py`. 신규 검증 기록: `docs/P4_CLIENT_RENDERED_OWNER_CHART_TABLE_20261019.md`.
