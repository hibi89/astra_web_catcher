# OHORA 10월 16일 연습용 수집본 — 격리 데이터 적재 시험

## 범위·보존
- 업로드된 `OHORA_20261016_RAW_286.zip` 및 `OHORA_Analysis_Ready_20261016_084112.zip`을 읽기 전용으로 파싱하고, Python `sqlite3.connect(':memory:')`에서 **독립적인 스테이징 계정·게시물·미디어 테이블**을 생성했다. 원본 데이터·기존 `nail_dashboard/data/nails.db`·앱 코드·검증 스냅샷은 변경하지 않았다.
- 원본 ZIP 검사 후 SHA-256 각각 `5d20f8e8bc7bab2bc7217c881d11a94d45e26a604b5cb16452236f186e843c3b`, `bc77130e89050c303502d6c88f2b37cc823bc7be28eed1de6b1d76a2e0a9d7d3` 원래 값과 동일. ZIP CRC 검사 두 건 PASS. 개별 ID/계정명/게시물 캡션/미디어 URL은 이 문서에 기록하지 않음.
- 실제 기존 Astra 웹 대시보드를 이 데이터로 실행한 것은 **아님**. 본 결과를 '대시보드 실데이터 연동 완료'라고 표기하지 않는다.

## 메모리 SQLite 독립 시험 결과
| 검사 | 값 | 판정 |
|---|---:|---|
| master accounts | 294 | PASS |
| collected posts | 1845 | PASS |
| post media | 5953 | PASS |
| FK violations | 0 | PASS |
| duplicated post_id | 0 | PASS |
| duplicated media_id | 0 | PASS |
| latest5 post-key orphans | 0 | PASS |
| likes+comments reactions available | 1224 | PARTIAL |
| likes null | 621/1845 = 33.66% | RETAIN NULL |
| source archive bytes altered | no | PASS |

컬럼 간 FK가 모두 유효하다는 사실은 **계정·게시물·미디어 관계 수준**의 무결성만 의미한다. 원본 사이트/Meta 전체 데이터의 완전성을 보장하지 않는다.

## 국가별 소스 추출 깊이·누락 편향
| 국가 | 전체/수집 계정 | 게시물 | 계정별 게시물 깊이 | 좋아요 미수집 | 측정 가능한 반응 |
|---|---|---:|---|---:|---:|
| KR | 100/97 | 485 | 97계정 × 5건 | 193 = 39.79% | 292 |
| US | 101/98 | 450 | 15계정 × 1건, 79 × 5건, 4 × 10건 | 97 = 21.56% | 353 |
| JP | 93/91 | 910 | 91계정 × 10건 | 331 = 36.37% | 579 |

측정 가능한 게시물 **부분집합**의 반응(좋아요+댓글) 평균/중앙값: KR 561.6/103, US 4628.6/609, JP 791.3/162. 해당 수치는 누락률·계정 규모·수집깊이·활동 기간이 다르므로 국가별 실제 시장 수요나 매출/흥행 순위로 해석하면 안 된다. 원본 `views` 및 구매 데이터 없음.

## 기존 Astra 매핑으로 확인된 제한
- `account_key`는 계정 식별자이지 **brand**가 아니다. 브랜드의 4개 가상 값과 임의 연결 금지.
- 현행 `posts.likes`는 `NOT NULL`인데 수집본의 621개가 NULL. 원본 결측을 0으로 변환하거나 임의 제외해 기존 전체 KPI인 것처럼 표시 금지. 별도 nullable staging/집계정책 승인 필요.
- `posted_at`·미디어 형식·followers snapshot은 존재하므로 샘플 주별/시간대/미디어 분포 계산 가능. **동일 수집 깊이/타임존** 확인 전 국가별 비교 부적절.
- `posts.purpose`, `treatment`, `analyzed`, `post_tags`의 AI 디자인 태그, 조회수 및 원본 수요·성과 지수 공식이 없음. UI 차트/인덱스는 계산 불가·미구현 표시 필요.
- `posts_latest5_per_account`는 자료 내 최신 최대5, 전 계정의 전체 게시물 최신5를 빠짐없이 API로 탐색했다는 증거는 아님.
- 내일 본수집은 **국가/계정별 동일 수집 깊이 혹은 기간** 및 8개 실패 재시도/좋아요 결측 원인 기록이 핵심. 실제 데이터 연결에 앞서 별도 staging→validation→approved copy 절차가 필요하다.

## Astra 최초 지침과 이번 실험의 관계
- 원 저장소 `REQUIREMENTS.md`: 독립 /shop(BookHarbor)·/jobs(CareerWay) **두 로컬 MVP** 구현이 최초 확인된 수락 범위. 해당 UI/API/DB 테스트는 이전에 별도 완료했다.
- 연구 브랜치의 추가 네일 대시보드는 4개 메뉴 및 가상 SQLite를 이용한 기능 재현 MVP로 Windows pytest 33/33·실제 HTTP 재시작·Playwright Chromium E2E를 **과거 사용자 실행 로그**로 검증했다.
- 이번 시험은 데이터 관계/결측 사전 점검이며, **범용 임의 URL 자동 웹캐쳐/실사용자 데이터 연동/프로덕션 출시는 완료 아님**. 별도 요구·설계가 있어야 한다.

**판정:** 이 연습 파일에 대한 독립 staging/FK 무결성 PASS, 데이터-지표 호환성은 부분만 가능. 기존 Astra 앱 소스·원본·스냅샷에 대한 변경 0건.
