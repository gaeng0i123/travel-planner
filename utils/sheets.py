import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

SHEET_URL = "https://docs.google.com/spreadsheets/d/12j2JaYTvnNmSUwJJ8zSWUuqJh5MUUe5JwftYYrz_6oY/edit?usp=sharing"
VND_TO_KRW = 0.054

# 워크시트명 → session_state.data 키 매핑
_SHEET_KEY = {
    "expenses":  "expenses",
    "checklist": "checklist",
    "budget":    "budget",
    "hotels":    "hotels",
    "상세일정":  "itinerary",
}

# set_page_config() 이후 임포트되므로 모듈 로드 시점에 연결 생성해도 안전
conn = st.connection("gsheets", type=GSheetsConnection)

def load_all_data() -> dict:
    try:
        budget_df    = conn.read(spreadsheet=SHEET_URL, worksheet="budget",   ttl=0)
        checklist_df = conn.read(spreadsheet=SHEET_URL, worksheet="checklist", ttl=0)
        hotels_df    = conn.read(spreadsheet=SHEET_URL, worksheet="hotels",   ttl=0)
        itinerary_df = conn.read(spreadsheet=SHEET_URL, worksheet="상세일정", ttl=0)
        try:
            expenses_df = conn.read(spreadsheet=SHEET_URL, worksheet="expenses", ttl=0)
        except Exception:
            expenses_df = pd.DataFrame(columns=["영수증ID", "날짜", "시간", "장소명", "품목", "단가", "수량", "총액(VND)", "환산금액(KRW)", "결제수단", "memo", "영수증URL", "저장시간"])

        return {
            "budget":    budget_df.to_dict("records"),
            "checklist": checklist_df.to_dict("records"),
            "hotels":    hotels_df.to_dict("records"),
            "itinerary": itinerary_df.to_dict("records"),
            "expenses":  expenses_df.to_dict("records"),
        }
    except Exception:
        return {"budget": [], "checklist": [], "hotels": [], "itinerary": [], "expenses": []}


# ── 오프라인 대기열 ────────────────────────────────────────────────────────────

def _ensure_queue():
    """session_state에 대기열과 즉시저장 설정 초기화"""
    if "sync_queue" not in st.session_state:
        st.session_state.sync_queue = {}   # {worksheet_name: df}
    if "offline_mode" not in st.session_state:
        st.session_state.offline_mode = False

def queue_update(df: pd.DataFrame, worksheet_name: str) -> None:
    """즉시 로컬 캐시에 반영하고 대기열에 적재 (API 호출 없음)."""
    _ensure_queue()
    # 로컬 캐시 즉시 갱신
    key = _SHEET_KEY.get(worksheet_name, worksheet_name)
    if st.session_state.get("data") is not None:
        st.session_state.data[key] = df.to_dict("records")
    # 대기열에 최신 상태 덮어쓰기 (같은 시트를 여러 번 수정해도 최신 1개만 유지)
    st.session_state.sync_queue[worksheet_name] = df

def flush_queue() -> tuple[int, list[str]]:
    """대기열의 모든 변경사항을 Google Sheets에 일괄 저장. (성공 수, 실패 목록) 반환."""
    _ensure_queue()
    queue = st.session_state.sync_queue
    if not queue:
        return 0, []
    ok, failed = 0, []
    for ws_name, df in list(queue.items()):
        try:
            conn.update(spreadsheet=SHEET_URL, worksheet=ws_name, data=df)
            del st.session_state.sync_queue[ws_name]
            ok += 1
        except Exception:
            failed.append(ws_name)
    return ok, failed

def pending_count() -> int:
    _ensure_queue()
    return len(st.session_state.sync_queue)


def update_sheet(df: pd.DataFrame, worksheet_name: str) -> None:
    """즉시 로컬 반영 + 대기열 적재. 오프라인 모드면 API 호출 생략."""
    queue_update(df, worksheet_name)
    if not st.session_state.get("offline_mode", False):
        # 온라인 모드: 바로 flush 시도
        flush_queue()
