import os
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_folium import st_folium
import folium
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# 사이트 설정
st.set_page_config(
    page_title="🇻🇳 2026 베트남 다낭 여행 ✈️", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- [모바일 감지 및 UI 스타일 정의] ---
st.markdown("""
    <style>
    /* 1. Streamlit 기본 헤더(포크/깃 아이콘 등) 숨기기 */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    /* 2. 전체 컨테이너 상단 여백 제로화 및 위로 끌어올리기 */
    .main .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0.5rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
    
    /* [모바일 전용 초밀착 설정] */
    @media (max-width: 640px) {
        .stApp {
            margin-top: -3.8rem !important; /* 위로 더 바싹 당김 */
        }
        .main .block-container {
            padding-top: 0rem !important;
            margin-top: 0rem !important;
        }
        /* 제목(h1) - 🇻🇳 베트남 다낭 여행 ✈️ 및 로그인 제목 */
        h1 {
            font-size: 25px !important; /* 시원하게 키움 */
            margin: 0 !important;
            padding: 0.6rem 0 0.3rem 0 !important;
            line-height: 1.1 !important;
            font-weight: 800 !important;
        }
        /* 동기화 버튼 텍스트 크기 (기존처럼 확보) */
        .stButton>button {
            font-size: 14.5px !important; 
            height: 2.3em !important;
        }
        /* 섹션 헤더 (h2) - 💰 1. 전체 예산 등 */
        h2 {
            font-size: 19px !important; /* 중간 제목 강조 */
            margin-top: 1.2rem !important;
            margin-bottom: 0.6rem !important;
            font-weight: bold !important;
        }
        /* 서브 헤더 (h3) */
        h3 {
            font-size: 17px !important;
            margin-top: 0.8rem !important;
            margin-bottom: 0.4rem !important;
        }
        /* 일반 텍스트 및 라벨 */
        .stMarkdown p, label {
            font-size: 14.5px !important;
        }
        /* 탭 버튼 글자 크기 */
        .stTabs [data-baseweb="tab"] {
            font-size: 0.85rem !important;
            padding: 5px 8px !important;
        }
        /* 입력창 라벨 간격 */
        .stTextInput label, .stSelectbox label, .stDateInput label {
            margin-bottom: 0rem !important;
        }
        /* [신규] 정보 박스(st.info) 높이 축소 */
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

# --- [로그인 시스템] ---
def check_password():
    """로컬 환경(LOCAL_DEV=1)에서는 로그인 스킵, 웹 배포 시에만 비밀번호 요구."""
    if os.environ.get("LOCAL_DEV") == "1":
        return True

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("🔒 Access Restricted")
        password = st.text_input("Please enter the access password", type="password")
        if st.button("Login"):
            if password == st.secrets["PASSWORD"]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ Incorrect password. Please try again.")
        return False
    return True

# 로그인 확인 후 진행
if not check_password():
    st.stop()

VND_TO_KRW = 0.054

# 구글 시트 연결 설정
# .streamlit/secrets.toml 파일에 아래 주소를 저장하거나 직접 입력 가능
SHEET_URL = "https://docs.google.com/spreadsheets/d/12j2JaYTvnNmSUwJJ8zSWUuqJh5MUUe5JwftYYrz_6oY/edit?usp=sharing"

# 데이터 로드 로직 (구글 시트 연동)
conn = st.connection("gsheets", type=GSheetsConnection)

def read_thinklog_from_docs():
    """구글 독스에서 thinklog 텍스트를 읽어옵니다."""
    try:
        s = st.secrets["connections"]["gsheets"]
        creds = Credentials.from_service_account_info(
            {
                "type": s["type"], "project_id": s["project_id"],
                "private_key_id": s["private_key_id"], "private_key": s["private_key"],
                "client_email": s["client_email"], "client_id": s["client_id"],
                "auth_uri": s["auth_uri"], "token_uri": s["token_uri"],
                "auth_provider_x509_cert_url": s["auth_provider_x509_cert_url"],
                "client_x509_cert_url": s["client_x509_cert_url"],
            },
            scopes=["https://www.googleapis.com/auth/documents.readonly"]
        )
        service = build("docs", "v1", credentials=creds)
        doc = service.documents().get(documentId=st.secrets["THINKLOG_DOC_ID"]).execute()
        paragraphs = []
        for element in doc.get("body", {}).get("content", []):
            if "paragraph" in element:
                line = ""
                for pe in element["paragraph"]["elements"]:
                    if "textRun" in pe:
                        line += pe["textRun"]["content"]
                paragraphs.append(line.rstrip("\n"))
        return "\n".join(paragraphs).strip()
    except Exception as e:
        return f"구글 독스 읽기 실패: {e}"

def load_all_data():
    try:
        budget_df = conn.read(spreadsheet=SHEET_URL, worksheet="budget", ttl=0)
        checklist_df = conn.read(spreadsheet=SHEET_URL, worksheet="checklist", ttl=0)
        hotels_df = conn.read(spreadsheet=SHEET_URL, worksheet="hotels", ttl=0)
        itinerary_df = conn.read(spreadsheet=SHEET_URL, worksheet="상세일정", ttl=0)
        return {
            "budget": budget_df.to_dict('records'),
            "checklist": checklist_df.to_dict('records'),
            "hotels": hotels_df.to_dict('records'),
            "itinerary": itinerary_df.to_dict('records'),
        }
    except Exception as e:
        return {"budget": [], "checklist": [], "hotels": [], "itinerary": []}

# 데이터 저장 로직 (구글 시트 업데이트)
def update_sheet(df, worksheet_name):
    conn.update(spreadsheet=SHEET_URL, worksheet=worksheet_name, data=df)
    st.session_state.data = load_all_data()

# 데이터 로드 및 세션 상태 초기화
if "data" not in st.session_state or st.session_state.data is None:
    st.session_state.data = load_all_data()

# 최종 데이터 변수 할당 (이 아래부터 data 변수 사용 가능)
data = st.session_state.data

# 탭 구성
col_title, col_btn = st.columns([3.5, 1.2])
# 제목이 길어져 비율 소폭 조정
with col_title:
    st.title("🇻🇳 베트남 다낭 여행 ✈️")
with col_btn:
    if st.button("🔄 동기화", use_container_width=True):
        st.session_state.data = load_all_data()
        st.rerun()

tab_prep, tab_trip, tab_ai = st.tabs(["🏗️ 여행 준비 (Live Sheets)", "🛵 여행 현지 (동선/영수증)", "💬 AI 여행 비서"])

# --- [1. 여행 준비 단계] ---
with tab_prep:
    st.info(f"🔗 연결된 구글 시트: [바로가기]({SHEET_URL})")
    
    # (1) 예산 관리
    st.header("💰 1. 전체 예산 및 사전 지출")
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        b_cat = st.selectbox("구분", ["항공권", "숙소", "보험", "유심/그랩", "기타"])

        if b_cat == "숙소":
            b_item = st.text_input("숙소명")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                b_checkin = st.date_input("체크인")
            with col_d2:
                b_checkout = st.date_input("체크아웃")
            nights = max((b_checkout - b_checkin).days, 0)
            b_price = st.number_input("1박 금액 (KRW)", min_value=0, step=10000)
            b_cost = nights * b_price
            col_m1, col_m2 = st.columns(2)
            col_m1.metric("박수", f"{nights}박")
            col_m2.metric("총 금액", f"{b_cost:,}원")
            b_memo = st.text_area("메모 (장단점)", height=80)
            b_cancel = st.text_input("무료 취소 기한 (예: 5/20 18:00까지)")
            b_paid = st.checkbox("결제 완료")
            if st.button("시트에 추가", key="add_hotel"):
                new_row = pd.DataFrame([{
                    "category": b_cat, "item": b_item,
                    "check_in": str(b_checkin), "check_out": str(b_checkout),
                    "nights": nights, "price_per_night": b_price,
                    "cost": b_cost, "cancel_deadline": b_cancel, 
                    "memo": b_memo, "paid": b_paid
                }])
                df_existing = pd.DataFrame(data["budget"]) if data["budget"] else pd.DataFrame()
                df_updated = pd.concat([df_existing, new_row], ignore_index=True)
                update_sheet(df_updated, "budget")
                st.success("구글 시트에 저장되었습니다!")
                st.rerun()
        else:
            with st.form("budget_form", clear_on_submit=True):
                b_item = st.text_input("항목명")
                b_cost = st.number_input("금액 (KRW)", min_value=0, step=1000)
                b_paid = st.checkbox("결제 완료")
                if st.form_submit_button("시트에 추가"):
                    new_row = pd.DataFrame([{
                        "category": b_cat, "item": b_item,
                        "check_in": "", "check_out": "",
                        "nights": 0, "price_per_night": 0,
                        "cost": b_cost, "memo": "", "paid": b_paid
                    }])
                    df_existing = pd.DataFrame(data["budget"]) if data["budget"] else pd.DataFrame()
                    df_updated = pd.concat([df_existing, new_row], ignore_index=True)
                    update_sheet(df_updated, "budget")
                    st.success("구글 시트에 저장되었습니다!")
                    st.rerun()

    with col2:
        if data["budget"]:
            df_b = pd.DataFrame(data["budget"])
            st.dataframe(df_b, use_container_width=True)
            total_b = pd.to_numeric(df_b["cost"], errors="coerce").sum()
            st.metric("총 사전 지출금액", f"{total_b:,.0f} 원")
        else:
            st.write("데이터를 입력해 주세요.")

    st.divider()

    # (2) 준비물 체크리스트
    st.header("🎒 2. 준비물 체크리스트")
    col_c1, col_c2 = st.columns(2)
    
    with col_c1:
        new_c_item = st.text_input("준비물 추가")
        if st.button("체크리스트 추가"):
            new_row = pd.DataFrame([{"item": new_c_item, "done": False}])
            df_existing = pd.DataFrame(data["checklist"])
            df_updated = pd.concat([df_existing, new_row], ignore_index=True)
            update_sheet(df_updated, "checklist")
            st.rerun()
            
    with col_c2:
        if data["checklist"]:
            df_c = pd.DataFrame(data["checklist"])
            # Google Sheets 빈 셀이 NaN(float64)으로 읽힐 수 있어 bool로 변환
            df_c["done"] = df_c["done"].apply(lambda x: bool(x) if pd.notna(x) and str(x).strip() not in ("", "nan", "None") else False)
            for i, row in df_c.iterrows():
                cur_val = bool(row["done"])
                checked = st.checkbox(row["item"], value=cur_val, key=f"c_{i}")
                if checked != cur_val:
                    df_c.at[i, "done"] = checked
                    update_sheet(df_c, "checklist")
                    st.rerun()

    st.divider()

    # (3) 예상 일정
    st.header("🗓️ 3. 예상 일정")
    if data["itinerary"]:
        df_i = pd.DataFrame(data["itinerary"])
        # memo 값 보존용 원본 저장
        original_확정 = df_i["확정"].copy()
        df_i["확정"] = df_i["확정"].apply(lambda x: str(x).strip().lower() in ("true", "1", "yes", "확정", "ok"))
        edited = st.data_editor(
            df_i,
            use_container_width=True,
            hide_index=True,
            height=35 * (len(df_i) + 1) + 10,
            column_config={
                "날짜": st.column_config.TextColumn("날짜", width="small"),
                "요일": st.column_config.TextColumn("요일", width="small"),
                "시간": st.column_config.TextColumn("시간", width="small"),
                "확정": st.column_config.CheckboxColumn("✅ 확정", width="small"),
                "내용": st.column_config.TextColumn("내용", width="large"),
                "메모": st.column_config.TextColumn("메모", width="medium"),
                "장소명": st.column_config.TextColumn("장소명", width="medium"),
                "구글지도": st.column_config.LinkColumn("구글지도", width="medium"),
                "lat": st.column_config.NumberColumn("lat", width="small"),
                "lon": st.column_config.NumberColumn("lon", width="small"),
                "소요시간": st.column_config.TextColumn("소요시간", width="small"),
                "이동시간": st.column_config.TextColumn("이동시간", width="small"),
            },
            disabled=["날짜","요일","시간","내용","메모","장소명","구글지도","lat","lon","소요시간","이동시간"],
        )
        if not edited["확정"].equals(df_i["확정"]):
            save_df = edited.copy()
            save_df["확정"] = save_df.apply(
                lambda row: "memo" if str(original_확정.iloc[row.name]).strip().lower() == "memo"
                            else ("ok" if row["확정"] else ""),
                axis=1
            )
            update_sheet(save_df, "상세일정")
            st.success("확정 상태가 저장되었습니다!")
            st.rerun()
    else:
        st.write("구글 시트 '상세일정' 탭에 데이터를 입력해 주세요.")

# --- [2. 여행 현지 단계] ---
with tab_trip:
    st.header("🛵 현지 실시간 관리")

    category_icon = {"에어컨카페": "☕", "스파": "💆"}

    # 확정된 일정 필터링 (내용이 있는 행만 — 빈 ok 행은 일차 버튼에서 제외)
    confirmed = [
        r for r in data["itinerary"]
        if str(r.get("확정", "")).strip().lower() in ("true", "1", "yes", "확정", "ok")
        and str(r.get("내용", "")).strip()
        and str(r.get("날짜", "")).strip()
    ]
    df_confirmed = pd.DataFrame(confirmed) if confirmed else pd.DataFrame()

    # 주요메모 장소 필터링 (좌표 있는 것만)
    memo_places = [
        r for r in data["itinerary"]
        if str(r.get("확정", "")).strip().lower() == "memo"
        and str(r.get("lat", "")).strip() not in ("", "nan")
        and str(r.get("lon", "")).strip() not in ("", "nan")
    ]

    # 카테고리 목록 (memo_places 기준)
    categories = []
    for r in memo_places:
        cat = str(r.get("내용", "")).strip()
        if cat and cat not in categories:
            categories.append(cat)

    if df_confirmed.empty and not memo_places:
        st.info("여행 준비 탭 예상일정에서 일정을 확정하면 여기에 표시됩니다.")
    else:
        # ── 세션 상태 초기화 ────────────────────────────────────────────────
        if "view_mode" not in st.session_state:
            st.session_state.view_mode = "day"
        if "selected_day" not in st.session_state:
            st.session_state.selected_day = 0
        if "memo_category" not in st.session_state or st.session_state.memo_category not in categories:
            st.session_state.memo_category = categories[0] if categories else ""

        # ── 1행: 일차 버튼 (고정 5일) ───────────────────────────────────────
        TRIP_DAYS = [
            ("5/30", "1일차(5/30,토)"),
            ("5/31", "2일차(5/31,일)"),
            ("6/1",  "3일차(6/1,월)"),
            ("6/2",  "4일차(6/2,화)"),
            ("6/3",  "5일차(6/3,수)"),
        ]
        dates      = [d for d, _ in TRIP_DAYS]
        day_labels = [l for _, l in TRIP_DAYS]

        day_cols = st.columns(len(TRIP_DAYS))
        for i, (col, (_, label)) in enumerate(zip(day_cols, TRIP_DAYS)):
            with col:
                is_active = st.session_state.view_mode == "day" and st.session_state.selected_day == i
                if st.button(label, use_container_width=True,
                             type="primary" if is_active else "secondary",
                             key=f"day_{i}"):
                    st.session_state.view_mode = "day"
                    st.session_state.selected_day = i
                    st.session_state.pop("map_center", None)
                    st.session_state.pop("map_zoom", None)
                    st.rerun()

        # ── 2행: 카테고리 버튼 (에어컨카페 / 스파) + 전체동선 ────────────────
        btn2_labels = [(cat, category_icon.get(cat, "📌"), "memo") for cat in categories]
        btn2_labels.append(("전체동선", "🗺️", "all"))
        btn2_cols = st.columns(len(btn2_labels))
        for ci, (col, (cat, icon, mode)) in enumerate(zip(btn2_cols, btn2_labels)):
            with col:
                if mode == "memo":
                    is_active = st.session_state.view_mode == "memo" and st.session_state.memo_category == cat
                else:
                    is_active = st.session_state.view_mode == "all"
                if st.button(f"{icon} {cat}", use_container_width=True,
                             type="primary" if is_active else "secondary",
                             key=f"cat_{ci}"):
                    st.session_state.view_mode = mode
                    if mode == "memo":
                        st.session_state.memo_category = cat
                    st.session_state.pop("map_center", None)
                    st.session_state.pop("map_zoom", None)
                    st.rerun()

        # ── 콘텐츠 영역 ─────────────────────────────────────────────────────
        def val(v):
            return "" if pd.isna(v) or str(v).strip() == "" else str(v).strip()

        if st.session_state.view_mode == "day":
            if st.session_state.selected_day >= len(TRIP_DAYS):
                st.session_state.selected_day = 0

            selected_date, selected_label = TRIP_DAYS[st.session_state.selected_day]
            df_day = df_confirmed[df_confirmed["날짜"] == selected_date].reset_index(drop=True) if not df_confirmed.empty else pd.DataFrame()

            # 스크롤 앵커 — caption 바로 위 (장소 클릭 시 여기부터 보이도록)
            st.markdown('<div id="trip-map-anchor"></div>', unsafe_allow_html=True)

            # 장소명 클릭 후 지도로 스크롤
            if st.session_state.get("scroll_to_map"):
                st.session_state.scroll_to_map = False
                components.html("""
                <script>
                function doScroll() {
                    var doc = window.parent.document;
                    var anchor = doc.getElementById('trip-map-anchor');
                    if (!anchor) return;
                    var anchorTop = anchor.getBoundingClientRect().top;
                    // PC: stMain 스크롤 컨테이너 직접 조작
                    var main = doc.querySelector('[data-testid="stMain"]');
                    var scrolled = false;
                    if (main) {
                        var before = main.scrollTop;
                        main.scrollTop += anchorTop - main.getBoundingClientRect().top;
                        if (main.scrollTop !== before) scrolled = true;
                    }
                    // 모바일(iOS 등): stMain이 안 먹히면 window 직접 스크롤
                    if (!scrolled) window.parent.scrollBy(0, anchorTop);
                }
                setTimeout(doScroll, 300);
                setTimeout(doScroll, 800);
                </script>
                """, height=1)

            st.caption(f"📅 {selected_label} — 확정 {len(df_day)}개")

            # 지도 (장소명 클릭 시 해당 핀으로 이동)
            map_center = st.session_state.get("map_center", [16.047079, 108.206230])
            map_zoom   = st.session_state.get("map_zoom", 13)
            m = folium.Map(location=map_center, zoom_start=map_zoom)

            # 일차 핀 + 경로선
            pins = []
            if not df_day.empty and "lat" in df_day.columns and "lon" in df_day.columns:
                coord_count = {}
                for i, row in df_day.iterrows():
                    if pd.notna(row.get("lat")) and pd.notna(row.get("lon")) and row.get("lat") != "" and row.get("lon") != "":
                        lat, lon = float(row["lat"]), float(row["lon"])
                        key = (lat, lon)
                        count = coord_count.get(key, 0)
                        coord_count[key] = count + 1
                        offset = 0.00015
                        offsets = [(0,0),(offset,0),(-offset,0),(0,offset),(0,-offset),(offset,offset),(-offset,-offset)]
                        if count < len(offsets):
                            lat += offsets[count][0]
                            lon += offsets[count][1]
                        pins.append((lat, lon, i+1, row.get('시간',''), row.get('내용',''), row.get('장소명',''), row.get('구글지도','')))

                if len(pins) >= 2:
                    folium.PolyLine(
                        locations=[(p[0], p[1]) for p in pins],
                        color="#FF4B4B", weight=2.5, opacity=0.7, dash_array="6"
                    ).add_to(m)

                for lat, lon, num, time_val, content, place, gmap_url in pins:
                    gmap_link = gmap_url or f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                    popup_html = (f"<b>{num}. {place or content}</b><br>{time_val}"
                                  f"<br><a href='{gmap_link}' target='_blank' style='color:#4A90D9;'>🗺️ 구글맵으로 보기</a>")
                    folium.Marker(
                        location=[lat, lon],
                        popup=folium.Popup(popup_html, max_width=220),
                        tooltip=f"{num}. {place or content}",
                        icon=folium.DivIcon(
                            html=f'<div style="background:#FF4B4B;color:white;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:14px;box-shadow:0 2px 4px rgba(0,0,0,0.3);">{num}</div>',
                            icon_size=(28, 28), icon_anchor=(14, 14)
                        )
                    ).add_to(m)

            # 주요메모 핀 (파란 📌)
            for r in memo_places:
                try:
                    mlat, mlon = float(r["lat"]), float(r["lon"])
                    mplace = str(r.get("장소명", "") or r.get("내용", "")).strip()
                    mmemo  = str(r.get("메모", "")).strip()
                    mgmap  = str(r.get("구글지도", "") or f"https://www.google.com/maps/search/?api=1&query={mlat},{mlon}")
                    popup_html = (f"<b>📌 {mplace}</b>" + (f"<br>{mmemo}" if mmemo else "")
                                  + f"<br><a href='{mgmap}' target='_blank' style='color:#4A90D9;'>🗺️ 구글맵으로 보기</a>")
                    folium.Marker(
                        location=[mlat, mlon],
                        popup=folium.Popup(popup_html, max_width=220),
                        tooltip=f"📌 {mplace}",
                        icon=folium.DivIcon(
                            html=f'<div style="background:#4A90D9;color:white;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-size:15px;box-shadow:0 2px 4px rgba(0,0,0,0.3);">📌</div>',
                            icon_size=(28, 28), icon_anchor=(14, 14)
                        )
                    ).add_to(m)
                except (ValueError, TypeError):
                    pass

            map_key = f"day_map_{map_center[0]}_{map_center[1]}_{map_zoom}"
            st_folium(m, use_container_width=True, height=500, key=map_key)

            # 해당 일차 일정 목록
            st.subheader(f"📋 {selected_label} 확정 일정")

            for i, row in df_day.iterrows():
                duration_str  = val(row.get('소요시간'))
                transport_str = val(row.get('이동시간'))
                duration_combined = f"{duration_str}({transport_str})" if duration_str and transport_str else duration_str or ""
                place   = val(row.get('장소명'))
                lat_v   = val(row.get('lat'))
                lon_v   = val(row.get('lon'))
                time_v  = val(row.get('시간'))
                content = val(row.get('내용'))
                memo    = val(row.get('메모'))

                # 1행: 번호. 시간 - 내용 - 소요시간
                row1_parts = [p for p in [time_v, content, duration_combined] if p]
                row1_text = " - ".join(row1_parts) if row1_parts else ""
                st.markdown(
                    f"<p style='font-size:13px;opacity:0.7;margin:8px 0 2px;'>"
                    f"<b>{i+1}.</b> {row1_text}</p>",
                    unsafe_allow_html=True,
                )

                # 2행: 📍 장소명 — 풀너비 버튼
                if place and lat_v and lon_v:
                    if st.button(f"📍  {place}", key=f"place_{i}", use_container_width=True):
                        st.session_state.map_center = [float(lat_v), float(lon_v)]
                        st.session_state.map_zoom = 16
                        st.session_state.scroll_to_map = True
                        st.rerun()
                elif place:
                    st.markdown(
                        f"<p style='font-size:15px;font-weight:600;margin:2px 0;'>📍 {place}</p>",
                        unsafe_allow_html=True,
                    )

                # 3행: 메모 (있을 때만)
                if memo:
                    st.markdown(
                        f"<p style='font-size:12px;opacity:0.65;margin:2px 0 6px;white-space:pre-wrap;'>{memo}</p>",
                        unsafe_allow_html=True,
                    )

                st.divider()

        elif st.session_state.view_mode == "memo" and st.session_state.memo_category:
            # 카테고리 모드: 선택된 카테고리 장소 목록 + 지도
            selected_memos = [r for r in memo_places if str(r.get("내용","")).strip() == st.session_state.memo_category]
            icon = category_icon.get(st.session_state.memo_category, "📌")

            # 스크롤 앵커 — caption 바로 위
            st.markdown('<div id="trip-map-anchor"></div>', unsafe_allow_html=True)

            # 클릭 후 지도로 스크롤
            if st.session_state.get("scroll_to_map"):
                st.session_state.scroll_to_map = False
                components.html("""
                <script>
                function doScroll() {
                    var doc = window.parent.document;
                    var anchor = doc.getElementById('trip-map-anchor');
                    if (!anchor) return;
                    var anchorTop = anchor.getBoundingClientRect().top;
                    // PC: stMain 스크롤 컨테이너 직접 조작
                    var main = doc.querySelector('[data-testid="stMain"]');
                    var scrolled = false;
                    if (main) {
                        var before = main.scrollTop;
                        main.scrollTop += anchorTop - main.getBoundingClientRect().top;
                        if (main.scrollTop !== before) scrolled = true;
                    }
                    // 모바일(iOS 등): stMain이 안 먹히면 window 직접 스크롤
                    if (!scrolled) window.parent.scrollBy(0, anchorTop);
                }
                setTimeout(doScroll, 300);
                setTimeout(doScroll, 800);
                </script>
                """, height=1)

            st.caption(f"{icon} {st.session_state.memo_category} — {len(selected_memos)}개")

            # 카테고리 지도
            memo_map_center = st.session_state.get("map_center", [16.047079, 108.206230])
            memo_map_zoom   = st.session_state.get("map_zoom", 12)
            m = folium.Map(location=memo_map_center, zoom_start=memo_map_zoom)
            for idx, r in enumerate(selected_memos, start=1):
                try:
                    mlat, mlon = float(r["lat"]), float(r["lon"])
                    mplace = str(r.get("장소명", "") or "").strip()
                    mmemo  = str(r.get("메모", "")).strip()
                    mgmap  = str(r.get("구글지도", "") or f"https://www.google.com/maps/search/?api=1&query={mlat},{mlon}")
                    popup_html = (f"<b>{idx}. {mplace}</b>" + (f"<br>{mmemo}" if mmemo else "")
                                  + f"<br><a href='{mgmap}' target='_blank' style='color:#4A90D9;'>🗺️ 구글맵으로 보기</a>")
                    folium.Marker(
                        location=[mlat, mlon],
                        popup=folium.Popup(popup_html, max_width=220),
                        tooltip=f"{idx}. {mplace}",
                        icon=folium.DivIcon(
                            html=f'<div style="background:#4A90D9;color:white;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-size:15px;box-shadow:0 2px 4px rgba(0,0,0,0.3);">📌</div>',
                            icon_size=(28, 28), icon_anchor=(14, 14)
                        )
                    ).add_to(m)
                except (ValueError, TypeError):
                    pass
            memo_map_key = f"memo_map_{memo_map_center[0]}_{memo_map_center[1]}"
            st_folium(m, use_container_width=True, height=400, key=memo_map_key)

            # 장소 목록 — 버튼으로 탭 가능
            for idx, r in enumerate(selected_memos):
                mplace = str(r.get("장소명", "") or "").strip()
                mmemo  = str(r.get("메모", "")).strip()
                mlat   = str(r.get("lat", "")).strip()
                mlon   = str(r.get("lon", "")).strip()

                if mplace and mlat and mlon:
                    if st.button(f"📌  {mplace}", key=f"memo_place_{idx}", use_container_width=True):
                        st.session_state.map_center = [float(mlat), float(mlon)]
                        st.session_state.map_zoom = 16
                        st.session_state.scroll_to_map = True
                        st.rerun()
                elif mplace:
                    st.markdown(f"<p style='font-size:15px;font-weight:600;margin:6px 0 2px;'>📌 {mplace}</p>", unsafe_allow_html=True)

                if mmemo:
                    st.markdown(f"<p style='font-size:12px;opacity:0.7;margin:2px 0 6px;white-space:pre-wrap;'>{mmemo}</p>", unsafe_allow_html=True)
                st.divider()

        elif st.session_state.view_mode == "all":
            # 전체 동선: 모든 일차 확정 일정을 한 지도에
            day_colors = ["#FF4B4B", "#FF8C00", "#2ECC71", "#9B59B6", "#1ABC9C"]
            st.caption("🗺️ 전체동선 — 5일 확정 일정")
            m = folium.Map(location=[16.047079, 108.206230], zoom_start=12)

            for day_idx, (date, label) in enumerate(TRIP_DAYS):
                color = day_colors[day_idx % len(day_colors)]
                df_d = df_confirmed[df_confirmed["날짜"] == date].reset_index(drop=True) if not df_confirmed.empty else pd.DataFrame()
                if df_d.empty or "lat" not in df_d.columns:
                    continue
                pins_d = []
                coord_count = {}
                for i, row in df_d.iterrows():
                    if pd.notna(row.get("lat")) and pd.notna(row.get("lon")) and row.get("lat") != "" and row.get("lon") != "":
                        lat, lon = float(row["lat"]), float(row["lon"])
                        key = (lat, lon)
                        count = coord_count.get(key, 0)
                        coord_count[key] = count + 1
                        offset = 0.00015
                        offsets = [(0,0),(offset,0),(-offset,0),(0,offset),(0,-offset),(offset,offset),(-offset,-offset)]
                        if count < len(offsets):
                            lat += offsets[count][0]
                            lon += offsets[count][1]
                        pins_d.append((lat, lon, i+1, row.get('시간',''), row.get('내용',''), row.get('장소명','')))

                if len(pins_d) >= 2:
                    folium.PolyLine(
                        locations=[(p[0], p[1]) for p in pins_d],
                        color=color, weight=2.5, opacity=0.8, dash_array="6",
                        tooltip=label
                    ).add_to(m)

                for lat, lon, num, time_val, content, place in pins_d:
                    popup_html = f"<b>[{label}] {num}. {place or content}</b><br>{time_val}"
                    folium.Marker(
                        location=[lat, lon],
                        popup=folium.Popup(popup_html, max_width=200),
                        tooltip=f"[{label}] {num}. {place or content}",
                        icon=folium.DivIcon(
                            html=f'<div style="background:{color};color:white;border-radius:50%;width:26px;height:26px;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:12px;box-shadow:0 2px 4px rgba(0,0,0,0.3);">{num}</div>',
                            icon_size=(26, 26), icon_anchor=(13, 13)
                        )
                    ).add_to(m)

            st_folium(m, use_container_width=True, height=600)

            # 일차별 범례
            legend_html = "".join(
                f'<span style="display:inline-block;margin:4px 8px;font-size:13px;">'
                f'<span style="background:{day_colors[i % len(day_colors)]};color:white;border-radius:50%;padding:2px 7px;font-weight:bold;">●</span> {label}'
                f'</span>'
                for i, (_, label) in enumerate(TRIP_DAYS)
            )
            st.markdown(legend_html, unsafe_allow_html=True)

# --- [3. AI 여행 비서 단계] ---
with tab_ai:
    st.header("💬 AI 여행 비서")

    # 구글 독스 thinklog 불러오기
    if st.button("🔄 독스에서 최신 내용 불러오기"):
        st.session_state.pop("thinklog", None)
        st.rerun()
    thinklog = st.session_state.get("thinklog") or read_thinklog_from_docs()
    st.session_state["thinklog"] = thinklog
    st.caption("📝 나의 여행 고민 로그 (구글 독스 원본)")
    with st.container(border=True):
        st.markdown("""
<style>
.thinklog{color:inherit;}
.thinklog h1{font-size:1.2rem !important;margin:8px 0 4px;color:inherit;}
.thinklog h2{font-size:1.05rem !important;margin:6px 0 3px;color:inherit;}
.thinklog h3{font-size:0.95rem !important;margin:4px 0 2px;color:inherit;}
.thinklog p{font-size:0.9rem !important;margin:2px 0;line-height:1.6;color:inherit;}
.thinklog li{font-size:0.9rem !important;line-height:1.6;color:inherit;}
</style>
""", unsafe_allow_html=True)
        st.markdown(f'<div class="thinklog">{thinklog}</div>', unsafe_allow_html=True)

    st.divider()

    st.markdown("### 🤖 AI에게 물어보기")
    st.info("Claude Code와 여행 고민을 대화한 뒤 **'정리해줘'** 라고 하면 대화 내용이 위 독스에 자동으로 기록됩니다.")
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        st.link_button("Gemini 열기", "https://gemini.google.com", use_container_width=True)
    with col_a2:
        st.link_button("Claude 열기", "https://claude.ai", use_container_width=True)
