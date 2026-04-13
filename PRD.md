# 제품 요구사항 정의서 (PRD): 베트남 스마트 여행 플래너

## 1. 개요 (Overview)
구글 시트를 데이터베이스로 활용하여 여행의 모든 단계(준비 ~ 현지)를 관리하는 스마트 플래너. 구글 독스에 작성한 여행 고민 로그를 앱에서 불러와 외부 AI(Gemini/Claude)에게 붙여넣어 상담하는 방식으로 운영.

## 2. 주요 기능 및 요구사항

### 2.1. 여행 준비 및 예산 (Preparation & Budget)
- **숙소 입력:** 숙소명, 체크인/체크아웃 날짜, 1박 금액 → 박수·총금액 자동계산, 무료 취소 기한, 메모.
- **일반 예산:** 항공권·보험·유심 등 항목별 금액 및 결제 완료 여부.
- **체크리스트:** 준비물 추가/체크, 구글 시트 실시간 반영.

### 2.2. AI 여행 비서 탭 (현재 방식)
- **구글 독스 thinklog 연동:** 앱에서 독스 내용을 불러와 표시.
- **외부 AI 바로가기:** Gemini / Claude 링크 버튼 제공.
- **운영 방법:** 앱에서 thinklog 내용 확인 후 AI 창에 붙여넣어 상담.

### 2.3. 보안 정책 (Security First)
- **비공개 DB:** 서비스 계정 방식으로 나만 접근 가능한 구글 시트 사용.
- **키 관리:** `key.json`은 로컬에서만 사용 후 삭제, 깃에 절대 포함 금지.
- **무비용 구축:** 구글 시트 무료 티어 + Streamlit Community Cloud 무료 배포.

## 3. 데이터 구조 (Google Sheets)
- `budget`: category, item, check_in, check_out, nights, price_per_night, cost, cancel_deadline, memo, paid
- `checklist`: item, done
- `hotels`: 이름, 가격, 취소기한, 링크, 장단점

## 4. 구글 독스
- **thinklog 문서:** 여행 고민 및 일정 로그 (앱이 서비스 계정으로 읽기 전용 접근)
- 수정은 구글 독스 앱/웹에서 직접.

## 5. 배포 구조
- **레포:** `github.com/gaeng0i123/travel-planner`
- **브랜치:** `dev` (개발) → `main` (배포)
- **호스팅:** Streamlit Community Cloud → https://travel-planner-0i.streamlit.app/

## 6. 이후 과제 (작업 예정)
- 현지 탭: VND 실시간 경비 입력 및 KRW 자동 환산
- 동선 지도: folium으로 방문지 경로 시각화
- 영수증 OCR: 사진 찍어서 자동 입력 (AI API 환경 구성 후)
