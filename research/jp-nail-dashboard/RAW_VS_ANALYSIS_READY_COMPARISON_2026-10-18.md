# OHORA 2026-10-16 수집 스냅샷 vs 분석 준비본 — 읽기 전용 교차 검증

## 범위·보존

사용자가 업로드한 `OHORA_20261016_RAW_286.zip`과 `OHORA_Analysis_Ready_20261016_084112.zip`을 압축 해제나 원본 재작성 없이 Python 표준 라이브러리의 zipfile/csv로 검사. 본 문서는 **행 집계 및 익명화된 교차검증 결과만** 기록. ZIP 및 CSV 내용, 인스타그램 아이디·이름·캡션·미디어 링크는 GitHub에 업로드하지 않음.

| 업로드 파일 | 크기 | SHA-256 |
|---|---:|---|
| OHORA_20261016_RAW_286.zip | 1,627,894 bytes | `5d20f8e8bc7bab2bc7217c881d11a94d45e26a604b5cb16452236f186e843c3b` |
| OHORA_Analysis_Ready_20261016_084112.zip | 2,359,954 bytes | `bc77130e89050c303502d6c88f2b37cc823bc7be28eed1de6b1d76a2e0a9d7d3` |

ZIP 내부 CRC 검사 두 건 PASS. 이전 제출 `account_list(2).csv`와 RAW ZIP 내부 `account_list.csv`의 SHA-256 동일 `fb539da915034df23fd6faccd598cc4caf7feaba631f9f8351c1afa2b88c2e8c`.

## 두 파일의 성격 (생성 주체에 대한 증거 제한)

- **RAW_286:** API 결과를 CSV로 저장한 수집 스냅샷 3종(각각 accounts/posts/media) + 계정 마스터 294행 + README. 이름에 RAW가 있지만 이 파일이 Meta의 변환 없는 원본 JSON이라는 의미는 아님. `engagement_count`와 `engagement_rate_pct` 등 가공/계산 필드도 존재.
- **Analysis_Ready:** 게시물 ID·미디어 ID로 결합된 분석 준비 테이블, 계정 커버리지/국가 요약/계정별 최신5·실패 계정 목록·manifest 포함. 내부 README에 '홍주님 분석용 통합본' 명시. AI 디자인 분류와 과거 게시물 50개 백필은 **미포함**. 구체적인 생성 모델/담당자가 GPT인지 파일만으로 확정할 수 없음.
- **데이터 분할/합계:** RAW latest5 176계정/880게시물/2,612미디어, latest1 15계정/15게시물/50미디어, latest10 95계정/950게시물/3,291미디어. 각각 post_id 집합은 상호 비중복. 합산 286계정/1,845게시물/5,953미디어.
- 전체 마스터 계정 294, 수집성공 286, 수집실패 8(모두 error_code 110). 기타 원본 account snapshot의 pending은 해당 스냅샷에서 미처리 표기일 뿐 최종 분석의 8개 실패와 혼동하지 말 것.
- Analysis Ready `posts_flat_for_analysis.csv`: 1,845 unique post_id; `media_merged.csv`: 5,953 unique media_id; `accounts_coverage.csv`: 294계정 중 collected 286, failed 8. `posts_latest5_per_account.csv`: 계정 286개에서 최신 5개까지 총 1,370건; 271계정 5건, 15계정 1건. 이는 **확보된 자료 중 최신5**이지 전체 인스타그램 역사에서 최신5를 완전 탐색한 증거가 아님.

## 국가 분포 (실측)

| 국가 | 마스터 계정 | 게시물 확보 계정 | 실패 계정 | 게시물 | 미디어 |
|---|---:|---:|---:|---:|---:|
| KR | 100 | 97 | 3 | 485 | 1480 |
| US | 101 | 98 | 3 | 450 | 1298 |
| JP | 93 | 91 | 2 | 910 | 3175 |
| 합계 | 294 | 286 | 8 | 1845 | 5953 |

## 실제 필드 수준 품질·교차 대조

- RAW 1,845행 대 Analysis Ready 1,845행 post_id 집합 일치, 중복/추가/탈락 0.
- Raw `timestamp`→analysis `posted_at`, `permalink`→`post_url`, `like_count`→`likes`, `comments_count`→`comments`: 1,845/1,845 값 완전 일치. `country`, `account_key`, `username`, `media_type`, `media_product_type`, `engagement_count`, `engagement_rate_pct`, `collected_at`도 모두 완전 일치. `original_source` 1,845/1,845 출처 레이블 일치.
- **캡션 13건은 가공본에서 한 글자 변경**: 원본에서 '-'로 시작하는 13개 문자열에 앞에 작은따옴표 한 글자 `'`가 삽입됨; 각 13건은 `analysis_caption == "'" + raw_caption`. 원문 요약·번역·재작성 증거가 아니고 Excel 안전 처리/문자열 이스케이프 추정이지만 실제 생성 이유는 확인 불가. 변환 전 RAW를 authoritative text로 보존해야 함.
- `media_merged.csv` 5,953행은 RAW 3개 미디어 파일에서 media_id로 합친 결과이고 **전체 12개 컬럼 값 완전 동일**, 차이 0. 포스트↔마스터 연결 누락 0, 미디어↔포스트 연결 누락 0.
- `followers_at_collection`는 각 출처 계정 스냅샷의 followers_count와 1,845행 모두 일치; `attached_media_rows`는 출처 media의 포스트별 행 수와 모두 일치. 유효 반응 `engagement_count == likes+comments` 검산 1,224건 전부 일치; engagement rate도 같은 기록된 follower 수 기준 0.001%p 이내 불일치 0.
- **좋아요 결측 621/1,845 = 약 33.66%**; 유효 좋아요+댓글+반응/참여율 1,224/1,845. 댓글 필드 값 존재 1,845건(0값 포함); 좋아요 실제 0은 4건으로 NULL과 구분; 댓글 0은 815건. 분석 준비본의 누락값을 0으로 치환하지 말 것.
- 캡션 결측 17건. 미디어 URL 결측 384/5,953개; ZIP 안에 이미지 파일 자체는 없음. 연결 URL은 만료 가능, 원본 게시물 날짜는 2023-05-04~2026-10-15로 국가별 표본 기간/개수 차이 큼. 단순 국가별 평균/유행 비교는 기간·계정수·결측률 보정 없이는 위험.
- 게시물의 media_type: CAROUSEL_ALBUM 909 / VIDEO 522 / IMAGE 414. media_product_type: FEED 1323 / REELS 522. `views`, `is_design_post`, 브랜드 매핑, 색상·기법·계절 등의 AI 디자인 분류 태그는 **없음**. 직접시술/시트형 브랜드 메타도 확정 정보 없음.
- 긴 Instagram ID는 **문자열** 유지(Excel 숫자 변환 방지). 집계는 294 **계정**을 294개 **브랜드**/게시물로 취급하지 않음.

## 현재 p4 로컬 MVP와의 연동 적합성 (검토만)

- **사용할 입력 초안:** 마스터=`account_list.csv`; 게시물 분석 테이블=`posts_flat_for_analysis.csv` (1,845건); 미디어 상세=`media_merged.csv`; 중복/누락 모니터링=`accounts_coverage.csv`; 최신 계정별 비교용=`posts_latest5_per_account.csv` (1,370건). ZIP 안의 `manifest.json`·README는 메타/한계 기록용.
- `posts.posted_at`은 원본 timestamp(ISO 타임존 포함)에서 날짜+시간대 변환 기준을 사용자와 정해야 함. `posts.medium`은 `media_type` / `media_product_type`으로 매핑 가능 후보지만, 명시적 변환표 승인 필요.
- 현행 demo `posts.likes/comments`는 NOT NULL이지만 실데이터 621개 좋아요 결측이 존재. 원본 NULL을 0으로 변환 금지, 별도 staging/결측 데이터 모델/지표 분모 정책 설계가 선행되어야 함. 기존 데모 DB를 reset/overwrite 금지.
- 기존 `brands` 4 가상 브랜드와 마스터 계정 294는 다른 엔터티. 별도의 계정 모델·브랜드 매핑/지역 뷰 설계 없이는 자동 넣지 않음. **대시보드 전체 구조 변경은 보류**.
- 확보 가능한 기본 값: 계정·국가·게시물 수, 미디어 유형/건수, 게시 기간, likes와 comments가 둘 다 있는 **부분 집계**, 계정별 follower snapshot(출처의 관측시점). 불가/미검증: 전체 반응 대표성, 조회수 기반 성과, 원본 수요/성과 지수, AI 태그 기반 네일 컬러·기법 트렌드, 브랜드 실체 연결.
- **다음 결정 의존성:** 사용자에게 RAW 보존/분석 준비본 사용 기준을 제안하되, 현재로서는 사용자의 원본 데이터 DB/API 연동 승인 및 결측 처리 정의가 필요. 코드·DB 변경, 외부 네트워크 호출 없음.

## 실제 검증 범위

Python 표준 라이브러리 zipfile/csv/hashlib/collections를 사용한 read-only ZIP 2건, 원본 계정 마스터와 SHA 대조, 1,845행 필드 단위 비교, 5,953행 미디어 전체 셀 대조, derived field 계산 확인. 두 ZIP CRC PASS. 검증된 Windows B MVP는 `snapshot/nail-atlas-b-e2e-verified-2026-10-18` 커밋 `343790e34967f0b20862d4ec7f5de8f084414234`로 보존, 수정 없음.
