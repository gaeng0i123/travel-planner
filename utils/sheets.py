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
        return {
            "budget":    budget_df.to_dict("records"),
            "checklist": checklist_df.to_dict("records"),
            "hotels":    hotels_df.to_dict("records"),
            "itinerary": itinerary_df.to_dict("records"),
        }
    except Exception:
        return {"budget": [], "checklist": [], "hotels": [], "itinerary": []}


def update_sheet(df: pd.DataFrame, worksheet_name: str) -> None:
    conn.update(spreadsheet=SHEET_URL, worksheet=worksheet_name, data=df)
    st.session_state.data = load_all_data()
