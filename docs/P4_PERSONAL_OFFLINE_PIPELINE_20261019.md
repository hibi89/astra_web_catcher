# P4 개인용 오프라인 통합 실행 (2026-10-19)

## 목적 및 현재 구현

기존 모듈을 **관찰 JSON → 검증된 미승인 기능 명세 → 선언 스키마 매핑 비교 → 차단된 generation preflight → 합성 미리보기 trace** 순서로 호출하는 단일 CLI를 추가했다.

이 명령은 **웹 URL을 자동 방문하거나 페이지에서 정보를 수집하지 않는다.** `--observation`은 사용자가 이미 수집한 관찰 JSON 파일 경로다. 고객 DB/API에 연결하지 않으며, 새 앱을 원본 사이트 행동대로 생성하지도 않는다. 샘플 미리보기는 기존 고정 FastAPI/SQLite 합성 데이터만 사용한다.

## 실행 (저장소 루트, Python 의존성 기설치 필요)

```powershell
python -m pytest -q tests/test_p4_personal_pipeline.py
python -m scripts.p4_personal_pipeline
python -m scripts.p4_personal_pipeline --generate
```

첫 CLI는 JSON 진단 요약만 stdout에 출력한다. `--generate`는 OS temp의 새 `astra-synth-*` 디렉터리를 만들고, 합성 데모와 비실행 trace 파일을 기록한다. 출력의 `preview_folder` 경로를 사용해 기존 검수기를 별도로 실행할 수 있다.

```powershell
python -m astra_contracts.synthetic_acceptance "위 명령에서 출력된 preview_folder 실제 경로"
```

**Windows 기존 TestClient timeout으로 acceptance가 멈출 수 있다. 이 경우 완료로 보고하지 않는다.** 기존 loopback HTTP 브라우저 테스트와 별도다. 기본 실행에는 네트워크 연결이나 브라우저가 필요하지 않다.

## 검증 상태

- GitHub 소스 및 4개 pytest 테스트 함수 추가·커밋 완료.
- **이 변경 이후 pytest, CLI, 생성 미리보기 acceptance는 아직 실제 실행하지 않았다.** GitHub 연결은 성공했지만 이 실행 환경에서 저장소 clone이 DNS 실패로 막혔다. 기존 53/53 등 수치는 이 파일에 대한 새 검증이 아니다.
- `generation_contract=blocked_pending_review`, 승인/고객 DB/배포 관련 false 유지. 코드 경로는 새 분리된 `scripts/p4_personal_pipeline.py`에만 추가했고 기존 모듈은 바꾸지 않았다.
- 실제 URL 입력→자동 관찰, 기존 DB 매핑/수정, 원본 기능 자동 재구현, 앱 내부 UI 통합은 미구현.
- 개인용 MVP 완료 조건: 위 pytest, dry run, generate 및 별도 synthetic acceptance 또는 loopback HTTP 수동 확인의 통과 증거가 필요하다.
