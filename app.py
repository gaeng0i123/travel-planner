import streamlit as st

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
from utils.auth import check_password      # noqa: E402
from utils.sheets import load_all_data     # noqa: E402
from tabs import prep, trip, ai            # noqa: E402

# 로그인
if not check_password():
    st.stop()

# 데이터 로드
if "data" not in st.session_state or st.session_state.data is None:
    st.session_state.data = load_all_data()
data = st.session_state.data

# 타이틀 + 동기화 버튼
col_title, col_btn = st.columns([3.5, 1.2])
with col_title:
    st.title("🇻🇳 베트남 다낭 여행 ✈️")
with col_btn:
    if st.button("🔄 동기화", use_container_width=True):
        st.session_state.data = load_all_data()
        st.rerun()

# 탭
tab_prep, tab_trip, tab_ai = st.tabs([
    "🏗️ 여행 준비 (Live Sheets)",
    "🛵 여행 현지 (동선/영수증)",
    "💬 AI 여행 비서",
])

with tab_prep:
    prep.render(data)

with tab_trip:
    trip.render(data)

with tab_ai:
    ai.render()
