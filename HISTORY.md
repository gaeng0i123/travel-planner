# ✈️ 프로젝트 작업 히스토리 (Travel Planner)

## 1. 프로젝트 주요 마일스톤
- [x] **2026-04-13:** 프로젝트 초기 PRD 작성 및 기술 스택(Python/Streamlit) 확정.
- [x] **UI 고도화:** '준비'와 '현지' 탭 분리 및 예산/체크리스트 기능 구현.
- [x] **보안 강화:** Google Cloud 서비스 계정(Service Account) 연동 및 `.streamlit/secrets.toml`을 통한 비공개 DB 구축.
- [x] **자동화 시스템:** `start.sh`(원클릭 실행) 및 `fix_secrets.py`(보안 키 자동 변환) 제작.
- [x] **secrets.toml 정상화:** 플레이스홀더 텍스트를 `fix_secrets.py`로 `key.json`에서 자동 변환하여 구글 시트 연동 완료.
- [x] **실시간 DB 동기화:** 구글 시트 API 연동 (`ttl=0` 설정으로 캐시 없이 실시간 반영).
- [x] **숙소 예산 폼 고도화:** 숙소 선택 시 체크인/체크아웃 → 박수 자동계산, 1박 금액 → 총금액 자동계산, 무료 취소 기한, 메모 필드 추가.
- [x] **구글 독스 thinklog 연동:** Gemini API 할당량 문제로 앱 내 AI 채팅 제거. 대신 구글 독스에서 여행 고민 로그를 읽어와 표시하고, Gemini/Claude 외부 링크 제공.
- [x] **GitHub 배포 준비:** 프로젝트를 `~/myproject/travel-planner/`로 정리, `key.json` 제거, `.gitignore` 보완.
- [x] **브랜치 전략 도입:** `main`(배포용) / `dev`(개발용) 분리. GitHub `gaeng0i123/travel-planner` 레포에 푸시 완료.

## 2. 해결된 주요 이슈
- **환경 설정:** 맥(Mac) 경로 문제를 가상 환경(`venv`)과 쉘 스크립트로 완전 해결.
- **보안 이슈:** '링크 공유'를 차단하고 서비스 계정 전용 이메일 편집자 권한 부여 방식으로 전환.
- **데이터 유실:** 로컬 JSON 파일 대신 구글 시트를 주 데이터베이스로 사용하여 모바일-PC 동기화 완료.
- **Gemini API 할당량:** 구글 클라우드 프로젝트에 결제 활성화 시 무료 할당량 0 문제 → 앱 내 AI 채팅 제거, 외부 AI 링크로 대체.
- **TOML 파싱 오류:** `secrets.toml`에서 최상단 키(`GEMINI_API_KEY`, `THINKLOG_DOC_ID`)가 `[connections.gsheets]` 섹션 하위로 인식되던 문제 → 섹션 위로 이동하여 해결.

## 3. 파일 목록 및 역할
- `app.py`: 메인 웹 애플리케이션 (예산, 체크리스트, thinklog 뷰어).
- `start.sh`: 맥에서 로컬 실행용 스크립트.
- `fix_secrets.py`: 구글 서비스 계정 JSON 키 → secrets.toml 자동 변환 도구.
- `thinklog.md`: 여행 고민 로그 백업본 (실제 운영은 구글 독스).
- `.streamlit/secrets.toml`: 구글 시트 서비스 계정 키, 독스 ID 보관소 (비공개, 깃 제외).

## 4. 현재 상태 및 다음 과제
- GitHub 레포 생성 및 `main`/`dev` 브랜치 푸시 완료.
- [x] **Streamlit Community Cloud 배포 완료:** https://travel-planner-0i.streamlit.app/
- **이후 과제:** 현지 탭 구현 (VND 경비 입력, 동선 지도).

---
*마지막 업데이트: 2026년 4월 13일*
