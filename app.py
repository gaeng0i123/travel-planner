import streamlit as st
import streamlit.components.v1 as components

# 반드시 첫 번째 Streamlit 명령
st.set_page_config(
    page_title="🇻🇳 2026 베트남 다낭 여행 ✈️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
    <style>
    header[data-testid="stHeader"] {
        display: none !important;
    }
    footer, #MainMenu, [data-testid="stStatusWidget"],
    [data-testid="stToolbar"], .viewerBadge_container__1QSob {
        display: none !important;
    }
    .main .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0.5rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
    @media (max-width: 640px) {
        .stApp {
            margin-top: -3.8rem !important;
        }
        .main .block-container {
            padding-top: 0rem !important;
            margin-top: 0rem !important;
        }
        h1 {
            font-size: 25px !important;
            margin: 0 !important;
            padding: 0.6rem 0 0.3rem 0 !important;
            line-height: 1.1 !important;
            font-weight: 800 !important;
        }
        .stButton>button {
            font-size: 14.5px !important;
            height: 2.3em !important;
        }
        h2 {
            font-size: 19px !important;
            margin-top: 1.2rem !important;
            margin-bottom: 0.6rem !important;
            font-weight: bold !important;
        }
        h3 {
            font-size: 17px !important;
            margin-top: 0.8rem !important;
            margin-bottom: 0.4rem !important;
        }
        .stMarkdown p, label {
            font-size: 14.5px !important;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 0.85rem !important;
            padding: 5px 8px !important;
        }
        .stTextInput label, .stSelectbox label, .stDateInput label {
            margin-bottom: 0rem !important;
        }
        div[data-testid="stAlert"] {
            padding: 0.3rem 0.6rem !important;
            margin-top: 0rem !important;
            margin-bottom: 0.5rem !important;
        }
        div[data-testid="stAlert"] div[data-testid="stMarkdownContainer"] p {
            font-size: 0.85rem !important;
            margin: 0 !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# 로컬 모듈 — set_page_config 이후에 임포트해야 conn 생성 순서가 안전
from utils.auth import check_password                              # noqa: E402
from utils.sheets import load_all_data, flush_queue, pending_count # noqa: E402
from tabs import prep, trip, expenses, history, ai                 # noqa: E402

# 로그인
if not check_password():
    st.stop()

# 데이터 로드
if "data" not in st.session_state or st.session_state.data is None:
    st.session_state.data = load_all_data()
data = st.session_state.data

# 오프라인 모드 초기화
if "offline_mode" not in st.session_state:
    st.session_state.offline_mode = False
if "sync_queue" not in st.session_state:
    st.session_state.sync_queue = {}

# 타이틀 + 동기화 버튼
pending = pending_count()
col_title, col_offline, col_btn = st.columns([3.0, 1.0, 1.2])
with col_title:
    st.title("🇻🇳 베트남 다낭 여행 ✈️")
with col_offline:
    offline_label = "✈️ 오프라인" if st.session_state.offline_mode else "🌐 온라인"
    if st.button(offline_label, use_container_width=True):
        st.session_state.offline_mode = not st.session_state.offline_mode
        st.rerun()
with col_btn:
    sync_label = f"🔄 동기화 ({pending})" if pending else "🔄 동기화"
    if st.button(sync_label, use_container_width=True):
        if pending:
            ok, failed = flush_queue()
            if failed:
                st.warning(f"저장 실패: {', '.join(failed)} — 인터넷 확인 후 재시도")
            else:
                st.toast(f"✅ {ok}개 항목 동기화 완료!")
        st.session_state.data = load_all_data()
        st.rerun()

# 핀 팝업에서 새 탭으로 열린 경우 — 탭 없이 경비 폼 바로 표시
q_params = st.query_params
if q_params.get("tab") == "expenses":
    place = q_params.get("place", "")
    if place:
        st.info(f"📍 **{place}** 경비 입력")
    st.markdown(
        "<div style='margin-bottom:8px;'>"
        "<button onclick='window.close()' style='"
        "width:100%;padding:14px;font-size:17px;font-weight:700;"
        "background:#555;color:white;border:none;border-radius:10px;"
        "cursor:pointer;letter-spacing:0.5px;'>"
        "✕ 이 탭 닫기 (지도로 돌아가기)"
        "</button></div>",
        unsafe_allow_html=True,
    )
    expenses.render(data)
else:
    # 일반 탭 내비게이션
    # 💰 경비 관리 탭으로 JS 강제 이동 (지도 핀 클릭 → 경비 버튼 클릭 시)
    if st.session_state.get("_goto_expenses"):
        exp_place = st.session_state.pop("_goto_expenses")
        st.session_state["expense_prefill"] = exp_place
        components.html("""<script>
        setTimeout(function(){
            var tabs = window.parent.document.querySelectorAll('[data-baseweb="tab"]');
            if (tabs && tabs[2]) tabs[2].click();
        }, 80);
        </script>""", height=0)

    # 📊 여행 경비내역 탭으로 JS 강제 이동 (경비 관리 탭의 "전체 내역" 버튼 클릭 시)
    if st.session_state.pop("_goto_history", False):
        components.html("""<script>
        setTimeout(function(){
            var tabs = window.parent.document.querySelectorAll('[data-baseweb="tab"]');
            if (tabs && tabs[3]) tabs[3].click();
        }, 80);
        </script>""", height=0)

    tab_prep, tab_trip, tab_exp, tab_hist, tab_ai = st.tabs([
        "🏗️ 여행 준비",
        "🛵 여행 현지",
        "💰 경비 관리",
        "📊 여행 경비내역",
        "💬 AI 여행 비서",
    ])

    with tab_prep:
        prep.render(data)

    with tab_trip:
        trip.render(data)

    with tab_exp:
        expenses.render(data)

    with tab_hist:
        history.render(data)

    with tab_ai:
        ai.render()
