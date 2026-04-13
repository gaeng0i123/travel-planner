# 제품 요구사항 정의서 (PRD): 베트남 스마트 여행 플래너

## 1. 개요
구글 시트를 데이터베이스로 활용하여 여행 준비부터 현지 관리까지 올인원으로 관리하는 플래너.
구글 독스에 작성한 여행 고민 로그를 앱에서 불러와 외부 AI(Gemini/Claude)와 상담하는 방식으로 운영.

## 2. 주요 기능

### 2.1. 여행 준비 탭
- **예산 관리:** 항공권·숙소·보험 등 항목별 입력. 숙소는 체크인/아웃 날짜로 박수·총금액 자동계산, 무료 취소 기한, 메모.
- **체크리스트:** 준비물 추가/완료 체크, 구글 시트 실시간 반영.
- **예상 일정:** 구글 시트 `상세일정` 탭 연동. 날짜/요일/시간/확정/내용/구글지도/메모 전체 표시. 확정 체크한 항목만 현지 탭 지도에 표시 예정.

### 2.2. AI 여행 비서 탭
- 구글 독스 thinklog 실시간 불러오기 (서비스 계정 읽기 전용).
- Gemini / Claude 외부 링크 버튼 제공.

### 2.3. 여행 현지 탭 (작업 예정)
- 확정된 일정만 folium 지도에 핀 표시.
- VND 실시간 경비 입력 → KRW 자동 환산.

### 2.4. 보안 정책
- 서비스 계정 방식으로 나만 접근 가능한 비공개 구글 시트.
- `key.json` 로컬 사용 후 삭제, 깃 포함 금지.
- 무비용 운영: 구글 시트 무료 + Streamlit Community Cloud 무료.

## 3. 데이터 구조 (Google Sheets)
- `budget`: category, item, check_in, check_out, nights, price_per_night, cost, cancel_deadline, memo, paid
- `checklist`: item, done
- `hotels`: 이름, 가격, 취소기한, 링크, 장단점
- `상세일정`: 날짜, 요일, 시간, 확정, 내용, 구글지도, 메모

## 4. 구글 독스
- **thinklog 문서:** 여행 고민 및 일정 로그. 앱이 서비스 계정으로 읽기 전용 접근.

## 5. 배포
- **레포:** `github.com/gaeng0i123/travel-planner` (Public)
- **브랜치:** `dev` 개발 → `main` 배포
- **URL:** https://travel-planner-0i.streamlit.app/
