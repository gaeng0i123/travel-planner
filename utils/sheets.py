import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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

@st.cache_resource
def _uploaded_ws() -> set:
    """백그라운드 업로드 완료된 워크시트명 추적 (스레드 → 메인 신호용)"""
    return set()

_SHEETS_TO_LOAD = ["budget", "checklist", "hotels", "상세일정", "expenses"]
_TTL = 60  # 60초 캐시 — 탭 전환/버튼 클릭 시 API 재호출 방지

def _read_sheet(worksheet: str) -> tuple[str, pd.DataFrame | None]:
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet, ttl=_TTL)
        return worksheet, df
    except Exception:
        return worksheet, None

def load_all_data() -> dict:
    result = {"budget": [], "checklist": [], "hotels": [], "itinerary": [], "expenses": []}
    try:
        # 5개 시트 병렬 로딩
        with ThreadPoolExecutor(max_workers=5) as ex:
            futures = {ex.submit(_read_sheet, ws): ws for ws in _SHEETS_TO_LOAD}
            for future in as_completed(futures):
                ws, df = future.result()
                if df is None:
                    if ws == "expenses":
                        df = pd.DataFrame(columns=["영수증ID", "날짜", "시간", "장소명", "품목", "단가", "수량", "총액(VND)", "환산금액(KRW)", "결제수단", "memo", "저장시간"])
                    else:
                        continue
                key = _SHEET_KEY.get(ws, ws)
                result[key] = df.to_dict("records")
    except Exception:
        pass
    return result


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
    # 백그라운드 업로드 완료된 항목을 sync_queue에서 정리
    done = _uploaded_ws()
    for ws in list(done):
        st.session_state.sync_queue.pop(ws, None)
    done.clear()
    return len(st.session_state.sync_queue)


def update_sheet(df: pd.DataFrame, worksheet_name: str) -> None:
    """로컬 즉시 반영 후 백그라운드에서 업로드 (non-blocking)."""
    queue_update(df, worksheet_name)
    if not st.session_state.get("offline_mode", False):
        df_copy = df.copy()
        done = _uploaded_ws()
        def _upload():
            try:
                conn.update(spreadsheet=SHEET_URL, worksheet=worksheet_name, data=df_copy)
                done.add(worksheet_name)
            except Exception:
                pass  # 실패 시 sync_queue에 남아서 동기화 버튼으로 재시도 가능
        threading.Thread(target=_upload, daemon=True).start()
