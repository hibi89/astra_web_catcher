> **[OWNER-DEV-EXECUTION-V2 | INACTIVE-SCOPE-GUARD | 2026-11-16]** [웹 Sol High 최초 전체 설계→웹 Sol Instant 주력 대량 구현→일괄 전체 CI/수정→Codex Sol Max·Astra Max 독립감사→웹 Sol High 최종 인수→OWNER GO 후 Luna Extra High 등록](https://github.com/hibi89/hackathon-command-center-2026/blob/kmong-productization/docs/strategy/OWNER_DEV_EXECUTION_CANONICAL_20261116.md)은 **향후 소유자가 이 프로젝트의 구현/상용화를 명시적으로 재개할 때** 적용할 일반 모델·검증 운영 순서다. 본 레포의 기존 목적/계약·고유 요구/보안/고객정보·원본·출시 승인, 현재 보류 상태는 유지하며 이번 문구로 개발 재개·크몽 SKU 편입·CI/배포/상용화 자동 실행 금지. 과거 일반 모델 전담/4개 슬롯/매회 CI 지시가 최신 V2를 덮지 않는다. 새 채팅은 정확 repo/branch HEAD·이 AGENTS→HANDOFF/STATUS→REQUIREMENTS/정본→실제 소스 확인 후 현재 미션만 수행.

> **[OWNER-FINAL-BLUEPRINT-100 | 2026-11-13 KST | 사용자 확정·전체 저장소 공통 최우선]** 제품의 **공식 최종완성률 분모는 사용자 확정 최종설계도 전체 100%만** 인정한다. 담당 총괄/작업자 임의로 설계 범위·가중치·완료 조건을 축소·변경하거나, 해커톤용 MVP·합성 테스트·CI PASS/개발 마일스톤 85%·95%를 최종완성률로 혼용하지 않는다. 최종 요구 ID→구현 코드→정확 SHA의 실제 검증→미구현/미검증을 추적하고 승인된 가중치로만 산정한다. 증거/가중치 없으면 **최종설계 기준 UNASSESSED(재산정 대기)**, 기존 수치는 **과거 내부 마일스톤**으로 보존. 크몽 상품은 반드시 해총 `kmong-productization` 원장에 최신 근거 동기화, [작업중]/등록완료/RELEASE HOLD·최종 승인 별도 보존. 모든 구형 상충 완성률 문구보다 이 사용자 최종 정책 우선. [공통 최종설계 산정 규칙](https://github.com/hibi89/hackathon-command-center-2026/blob/kmong-productization/docs/strategy/FINAL_BLUEPRINT_COMPLETION_STANDARD_20261113.md). 정책 반영만으로 기존 제품 점수 재산정·기능 완료·배포 증명이 아니다.

> **[KMONG_WORK_TARGET_GATE_20261112 | 사용자 최신 확정 | 필수 작업 규칙]** 이 저장소에서 크몽 상품·육성 후보를 작업하는 모든 AI 담당자는 새 채팅·`ㄱ` 시작 시 이 문구를 읽고 적용한다.
> - 실제 개발/수정/테스트 착수 즉시 [해총 크몽 최종완성률·후보 상태표](https://github.com/hibi89/hackathon-command-center-2026/blob/kmong-productization/docs/audits/KMONG_16_CURRENT_20261111.md)의 **해당 상품명 옆에 `**[작업중]**`을 표시하고 GitHub 커밋**한다. 확정 단계 목표(예: 95%)와 검증 기준을 제품 STATUS/HANDOFF에 남긴다.
> - **목표 완성률 달성 전에는 [작업중]을 삭제하지 않는다.** 일시중단·종료·보류·다른 제품 전환·담당 채팅 변경도 삭제 사유가 아니다. 예전 '전환·중단 시 삭제' 지시는 폐기한다.
> - **검증된 목표치에 도달한 뒤에만** 기능 SHA·PASS/FAIL/SKIP·미검증을 기록하고 자기 표시를 제거·커밋한다. 목표 하향/변경으로 표식 제거 시 사용자 명시 승인 필요. 다른 담당자 표시·기존 수치·RELEASE HOLD 보존.
> - 표식은 목표 미달 상태를 의미하며 **실시간 실행 증명은 아니다**. 허브 최신 HEAD 확인 후 안전하게 반영, 실패 시 `KMONG_HUB_SYNC_PENDING` 기록. 자동 동기화 없음. 크몽 외 작업에는 표시 불필요.

> **2026-10-28 해총 전 저장소 최상위 공통 운영 공지 (소유자 승인):** [개발 가속·로컬검증·병목제거 통합 정본](https://github.com/hibi89/hackathon-command-center-2026/blob/main/docs/DEV_ACCELERATION_AND_VERIFICATION_20261028.md) 확인. 현 시점 활성은 **KIC(+DL)·PayPal·UGREEN·LA 4개**만이다. 이 프로젝트는 **임시 개발 대기**(폐기·기존 기록 삭제 아님)로, 소유자의 재개 지시 없이 `ㄱ`만으로 신규 개발·CI·배포를 진행하지 않는다. 활성 프로젝트 일반 기능 구현은 **GPT-6 Instant**, 최초 설계·난제·해총 독립검수는 높은 추론. 파일 단위 GitHub 반복·다수 상태 문서 갱신·동일 SHA 반복 조회를 줄이고, 기능 단위 검증/정확한 PASS·FAIL·SKIP·커밋 SHA만 보고한다. 기존 제품 설계 동결, 외부 승인, 보안·고객데이터/원본·출시 게이트는 그대로 유지. 이 공지는 운영 통지이며 기능 완성 선언이 아니다.

# Astra Web Catcher — Development Rules

- This repository is the intended code/version source of truth; do not confuse a locally generated ZIP with a GitHub push.
- Preserve existing working functionality and user data; back up before destructive migrations.
- Work in small vertical slices: UI → own API → DB → tests. Do not clone original site assets or use private APIs.
- Browser observation must be attributed only to pages actually inspected. Never bypass login, CAPTCHA or rate limits.
- All authentication decisions are server-side, based on HttpOnly session cookie. Filter private data by session owner.
- All financial amounts in integer won, order line snapshots immutable. Preserve `BEGIN IMMEDIATE` plus conditional stock decrement.
- Maintain unique constraints for cart, request keys, bookmarks, applications. Test parallel requests against separate SQLite DB.
- Never use production credentials or payment details. Demo accounts are for localhost only.
- Record actual test command/status, not assumptions. Browser automation blocked is a limitation, not a pass.
- On meaningful change update README/ARCHITECTURE/TEST-REPORT/REVIEW-PACK, STATUS.md and HANDOFF.md, then GitHub when supported.
