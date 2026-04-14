import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

SHEET_URL = "https://docs.google.com/spreadsheets/d/12j2JaYTvnNmSUwJJ8zSWUuqJh5MUUe5JwftYYrz_6oY/edit?usp=sharing"
VND_TO_KRW = 0.054

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
            # expenses 시트가 아직 없을 경우 빈 데이터프레임 생성
            expenses_df = pd.DataFrame(columns=["영수증ID", "날짜", "시간", "장소명", "품목", "단가", "수량", "총액(VND)", "환산금액(KRW)", "결제수단", "memo", "영수증URL"])
        
        return {
            "budget":    budget_df.to_dict("records"),
            "checklist": checklist_df.to_dict("records"),
            "hotels":    hotels_df.to_dict("records"),
            "itinerary": itinerary_df.to_dict("records"),
            "expenses":  expenses_df.to_dict("records"),
        }
    except Exception:
        return {"budget": [], "checklist": [], "hotels": [], "itinerary": [], "expenses": []}

def update_sheet(df: pd.DataFrame, worksheet_name: str) -> None:
    conn.update(spreadsheet=SHEET_URL, worksheet=worksheet_name, data=df)
    st.session_state.data = load_all_data()
