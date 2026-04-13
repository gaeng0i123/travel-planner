# 제품 요구사항 정의서 (PRD): 베트남 스마트 여행 플래너

## 1. 개요
구글 시트를 데이터베이스로 활용하여 여행 준비부터 현지 관리까지 올인원으로 관리하는 플래너.
구글 독스에 작성한 여행 고민 로그를 앱에서 불러와 외부 AI(Gemini/Claude)와 상담하는 방식으로 운영.

## 2. 주요 기능

### 2.1. 보안
- **로그인 시스템:** `st.secrets` 기반 비밀번호 인증. 인증 성공 시에만 앱 데이터 로드.

### 2.2. 여행 준비 탭
- **모바일 최적화:** 폰 접속 시 상단 여백 제거(0rem), Streamlit 헤더 숨김, 제목/버튼 한 줄 배치. 폰트 위계: h1 25px, h2 19px, 본문/버튼 14.5px.
- **예산 관리:** 항공권·숙소·보험 등 항목별 입력. 숙소는 체크인/아웃 날짜로 박수·총금액 자동계산, 무료 취소 기한, 메모.
- **체크리스트:** 준비물 추가/완료 체크, 구글 시트 실시간 반영.
- **예상 일정:** 구글 시트 `상세일정` 탭 연동. ✅ 확정 체크박스 클릭 시 `ok`로 시트 저장. 확정된 항목만 현지 탭 지도에 표시.

### 2.3. 여행 현지 탭
- **1일차~N일차 버튼:** 날짜 기준 자동 생성. 버튼 전환 시 시트 재조회 없이 빠르게 동작 (session_state 캐시).
- **지도:** 확정 일정만 번호 핀(1,2,3...) 표시. 핀 순서대로 점선 연결. 동일 좌표 핀은 오프셋으로 분리 표시.
- **일정 목록:** 지도 아래 HTML 테이블로 시간순 표시. 컬럼: #·시간·내용·소요(이동수단)·메모. 메모 줄바꿈(\n → `<br>`) 지원.
- **(예정) 경비 입력:** VND 실시간 경비 입력 → KRW 자동 환산.
- **(예정) 영수증 OCR:** AI API 환경 구성 후 추가.

### 2.4. AI 여행 비서 탭
- 구글 독스 thinklog 실시간 불러오기 (서비스 계정 읽기 전용).
- 헤딩(h1/h2/h3) CSS 소형화로 가독성 개선.
- Gemini / Claude 외부 링크 버튼 제공.

### 2.5. 보안 정책
- 서비스 계정 방식으로 나만 접근 가능한 비공개 구글 시트.
- `key.json` 로컬 사용 후 삭제, 깃 포함 금지.
- 무비용 운영: 구글 시트 무료 + Streamlit Community Cloud 무료.

## 3. 데이터 구조 (Google Sheets)
- `budget`: category, item, check_in, check_out, nights, price_per_night, cost, cancel_deadline, memo, paid
- `checklist`: item, done
- `hotels`: 이름, 가격, 취소기한, 링크, 장단점
- `상세일정`: 날짜, 요일, 시간, 확정(ok/빈값), 내용, 메모, 장소명, 구글지도, lat, lon, 소요시간, 이동시간

## 4. 구글 독스
- **thinklog 문서:** 여행 고민 및 일정 로그. 앱이 서비스 계정으로 읽기 전용 접근.
- 수정은 구글 독스 앱/웹에서 직접.

## 5. 로컬 디렉토리 구조
```
~/myproject/
└── travel-planner/       ← 실제 프로젝트 (깃 루트)
    ├── app.py
    ├── start.sh           ← 실행 시 travel-planner/venv/ 자동 생성
    ├── fix_secrets.py     ← key.json → secrets.toml 변환 도구
    ├── requirements.txt
    ├── .streamlit/
    │   └── secrets.toml  ← 비공개 (깃 제외)
    ├── HISTORY.md
    └── PRD.md
```

## 6. 배포
- **레포:** `github.com/gaeng0i123/travel-planner` (Public)
- **브랜치:** `dev` 개발 → `main` 배포
- **URL:** https://travel-planner-0i.streamlit.app/
