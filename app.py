import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_folium import st_folium
import folium
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# 사이트 설정
st.set_page_config(page_title="🇻🇳 베트남 여행 올인원 플래너", layout="wide")
VND_TO_KRW = 0.054

# 구글 시트 연결 설정
# .streamlit/secrets.toml 파일에 아래 주소를 저장하거나 직접 입력 가능
SHEET_URL = "https://docs.google.com/spreadsheets/d/12j2JaYTvnNmSUwJJ8zSWUuqJh5MUUe5JwftYYrz_6oY/edit?usp=sharing"

st.title("🇻🇳 베트남 여행 스마트 매니저 (Live DB)")

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
        text = ""
        for element in doc.get("body", {}).get("content", []):
            if "paragraph" in element:
                for pe in element["paragraph"]["elements"]:
                    if "textRun" in pe:
                        text += pe["textRun"]["content"]
        return text.strip()
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

# 데이터는 session_state에 캐시 → 동기화 버튼 누를 때만 재로딩
if "data" not in st.session_state:
    st.session_state.data = load_all_data()
data = st.session_state.data

# 탭 구성
col_title, col_btn = st.columns([5, 1])
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
            for i, row in df_c.iterrows():
                # 체크박스 상태 변경 시 즉시 시트 업데이트 (속도가 느릴 수 있음)
                checked = st.checkbox(row["item"], value=row["done"], key=f"c_{i}")
                if checked != row["done"]:
                    df_c.at[i, "done"] = checked
                    update_sheet(df_c, "checklist")
                    st.rerun()

    st.divider()

    # (3) 예상 일정
    st.header("🗓️ 3. 예상 일정")
    if data["itinerary"]:
        df_i = pd.DataFrame(data["itinerary"])
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
            save_df["확정"] = save_df["확정"].apply(lambda x: "ok" if x else "")
            update_sheet(save_df, "상세일정")
            st.success("확정 상태가 저장되었습니다!")
            st.rerun()
    else:
        st.write("구글 시트 '상세일정' 탭에 데이터를 입력해 주세요.")

# --- [2. 여행 현지 단계] ---
with tab_trip:
    st.header("🛵 현지 실시간 관리")

    # 확정된 일정만 필터링
    confirmed = [r for r in data["itinerary"] if str(r.get("확정", "")).strip().lower() in ("true", "1", "yes", "확정", "ok")]
    df_confirmed = pd.DataFrame(confirmed) if confirmed else pd.DataFrame()

    if df_confirmed.empty:
        st.info("여행 준비 탭 예상일정에서 일정을 확정하면 여기에 표시됩니다.")
    else:
        # 날짜 기준 1일차, 2일차... 버튼
        dates = sorted(df_confirmed["날짜"].dropna().unique())
        day_labels = [f"{i+1}일차" for i in range(len(dates))]

        if "selected_day" not in st.session_state:
            st.session_state.selected_day = 0

        cols = st.columns(len(dates))
        for i, (col, label) in enumerate(zip(cols, day_labels)):
            with col:
                btn_type = "primary" if st.session_state.selected_day == i else "secondary"
                if st.button(label, use_container_width=True, type=btn_type, key=f"day_{i}"):
                    st.session_state.selected_day = i
                    st.rerun()

        # 선택된 날짜 일정
        selected_date = dates[st.session_state.selected_day]
        df_day = df_confirmed[df_confirmed["날짜"] == selected_date].reset_index(drop=True)
        st.caption(f"📅 {selected_date} ({day_labels[st.session_state.selected_day]}) — 확정 {len(df_day)}개")

        # 지도 (다낭 중심)
        m = folium.Map(location=[16.047079, 108.206230], zoom_start=13)

        if "lat" in df_day.columns and "lon" in df_day.columns:
            pins = []
            coord_count = {}

            for i, row in df_day.iterrows():
                if pd.notna(row.get("lat")) and pd.notna(row.get("lon")) and row.get("lat") != "" and row.get("lon") != "":
                    lat, lon = float(row["lat"]), float(row["lon"])
                    key = (lat, lon)
                    count = coord_count.get(key, 0)
                    coord_count[key] = count + 1
                    # 같은 좌표면 살짝 오프셋 (나선형으로 벌림)
                    offset = 0.00015
                    offsets = [(0,0),(offset,0),(-offset,0),(0,offset),(0,-offset),(offset,offset),(-offset,-offset)]
                    if count < len(offsets):
                        lat += offsets[count][0]
                        lon += offsets[count][1]
                    pins.append((lat, lon, i+1, row.get('시간',''), row.get('내용',''), row.get('장소명','')))

            # 경로 선 연결
            if len(pins) >= 2:
                folium.PolyLine(
                    locations=[(p[0], p[1]) for p in pins],
                    color="#FF4B4B", weight=2.5, opacity=0.7, dash_array="6"
                ).add_to(m)

            # 핀 찍기
            for lat, lon, num, time_val, content, place in pins:
                popup_html = f"<b>{num}. {place or content}</b><br>{time_val}"
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(popup_html, max_width=200),
                    tooltip=f"{num}. {place or content}",
                    icon=folium.DivIcon(
                        html=f'<div style="background:#FF4B4B;color:white;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:14px;box-shadow:0 2px 4px rgba(0,0,0,0.3);">{num}</div>',
                        icon_size=(28, 28), icon_anchor=(14, 14)
                    )
                ).add_to(m)
        else:
            st.info("📍 구글 지도 링크에서 좌표를 추출하면 핀이 표시됩니다.")

        st_folium(m, use_container_width=True, height=500)

        # 해당 일차 일정 목록
        st.subheader(f"📋 {day_labels[st.session_state.selected_day]} 확정 일정")

        def val(v):
            return "" if pd.isna(v) or str(v).strip() == "" else str(v).strip()

        rows = []
        for i, row in df_day.iterrows():
            duration_str = val(row.get('소요시간'))
            transport_str = val(row.get('이동시간'))
            duration_combined = f"{duration_str}({transport_str})" if duration_str and transport_str else duration_str or ""
            rows.append({
                "#": i + 1,
                "시간": val(row.get('시간')),
                "내용": val(row.get('내용')),
                "소요(이동)": duration_combined,
                "메모": val(row.get('메모')),
            })

        df_display = pd.DataFrame(rows)
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "#": st.column_config.NumberColumn("#", width=40),
                "시간": st.column_config.TextColumn("시간", width="small"),
                "내용": st.column_config.TextColumn("내용", width="medium"),
                "소요(이동)": st.column_config.TextColumn("소요(이동)", width="small"),
                "메모": st.column_config.TextColumn("메모", width="large"),
            }
        )

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
        st.markdown(thinklog)

    st.divider()

    st.markdown("### 🤖 AI에게 물어보기")
    st.info("위 내용을 복사해서 AI에게 붙여넣으면 맥락을 바로 이해합니다.")
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        st.link_button("Gemini 열기", "https://gemini.google.com", use_container_width=True)
    with col_a2:
        st.link_button("Claude 열기", "https://claude.ai", use_container_width=True)
