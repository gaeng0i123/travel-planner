import streamlit as st
import pandas as pd
from utils.sheets import update_sheet, SHEET_URL


def render(data: dict) -> None:
    st.info(f"🔗 연결된 구글 시트: [바로가기]({SHEET_URL})")

    # ── (1) 예산 관리 ──────────────────────────────────────────────────────────
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
            b_memo   = st.text_area("메모 (장단점)", height=80)
            b_cancel = st.text_input("무료 취소 기한 (예: 5/20 18:00까지)")
            b_paid   = st.checkbox("결제 완료")
            if st.button("시트에 추가", key="add_hotel"):
                new_row = pd.DataFrame([{
                    "category": b_cat, "item": b_item,
                    "check_in": str(b_checkin), "check_out": str(b_checkout),
                    "nights": nights, "price_per_night": b_price,
                    "cost": b_cost, "cancel_deadline": b_cancel,
                    "memo": b_memo, "paid": b_paid,
                }])
                df_existing = pd.DataFrame(data["budget"]) if data["budget"] else pd.DataFrame()
                df_updated  = pd.concat([df_existing, new_row], ignore_index=True)
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
                        "cost": b_cost, "memo": "", "paid": b_paid,
                    }])
                    df_existing = pd.DataFrame(data["budget"]) if data["budget"] else pd.DataFrame()
                    df_updated  = pd.concat([df_existing, new_row], ignore_index=True)
                    update_sheet(df_updated, "budget")
                    st.success("구글 시트에 저장되었습니다!")
                    st.rerun()

    with col2:
        if data["budget"]:
            df_b    = pd.DataFrame(data["budget"])
            st.dataframe(df_b, use_container_width=True)
            total_b = pd.to_numeric(df_b["cost"], errors="coerce").sum()
            st.metric("총 사전 지출금액", f"{total_b:,.0f} 원")
        else:
            st.write("데이터를 입력해 주세요.")

    st.divider()

    # ── (2) 준비물 체크리스트 ──────────────────────────────────────────────────
    st.header("🎒 2. 준비물 체크리스트")
    col_c1, col_c2 = st.columns(2)

    with col_c1:
        new_c_item = st.text_input("준비물 추가")
        if st.button("체크리스트 추가"):
            new_row    = pd.DataFrame([{"item": new_c_item, "done": False}])
            df_existing = pd.DataFrame(data["checklist"])
            df_updated  = pd.concat([df_existing, new_row], ignore_index=True)
            update_sheet(df_updated, "checklist")
            st.rerun()

    with col_c2:
        if data["checklist"]:
            df_c = pd.DataFrame(data["checklist"])
            df_c["done"] = df_c["done"].apply(
                lambda x: bool(x) if pd.notna(x) and str(x).strip() not in ("", "nan", "None") else False
            )
            for i, row in df_c.iterrows():
                cur_val = bool(row["done"])
                checked = st.checkbox(row["item"], value=cur_val, key=f"c_{i}")
                if checked != cur_val:
                    df_c.at[i, "done"] = checked
                    update_sheet(df_c, "checklist")
                    st.rerun()

    st.divider()

    # ── (3) 예상 일정 ──────────────────────────────────────────────────────────
    st.header("🗓️ 3. 예상 일정")
    if data["itinerary"]:
        df_i = pd.DataFrame(data["itinerary"])
        original_확정 = df_i["확정"].copy()
        df_i["확정"] = df_i["확정"].apply(
            lambda x: str(x).strip().lower() in ("true", "1", "yes", "확정", "ok")
        )
        edited = st.data_editor(
            df_i,
            use_container_width=True,
            hide_index=True,
            height=35 * (len(df_i) + 1) + 10,
            column_config={
                "날짜":    st.column_config.TextColumn("날짜",    width="small"),
                "요일":    st.column_config.TextColumn("요일",    width="small"),
                "시간":    st.column_config.TextColumn("시간",    width="small"),
                "확정":    st.column_config.CheckboxColumn("✅ 확정", width="small"),
                "내용":    st.column_config.TextColumn("내용",    width="large"),
                "메모":    st.column_config.TextColumn("메모",    width="medium"),
                "장소명":  st.column_config.TextColumn("장소명",  width="medium"),
                "소요시간": st.column_config.TextColumn("소요시간", width="small"),
                "이동시간": st.column_config.TextColumn("이동시간", width="small"),
                "구글지도": st.column_config.LinkColumn("구글지도", width="medium"),
                "lat":    st.column_config.NumberColumn("lat",   width="small"),
                "lon":    st.column_config.NumberColumn("lon",   width="small"),
                "open":   st.column_config.TextColumn("오픈",    width="small"),
                "close":  st.column_config.TextColumn("마감",    width="small"),
            },
            disabled=[
                "날짜", "요일", "시간", "내용", "메모", "장소명",
                "소요시간", "이동시간", "구글지도", "lat", "lon", "open", "close",
            ],
        )
        if not edited["확정"].equals(df_i["확정"]):
            save_df = edited.copy()
            save_df["확정"] = save_df.apply(
                lambda row: "memo" if str(original_확정.iloc[row.name]).strip().lower() == "memo"
                            else ("ok" if row["확정"] else ""),
                axis=1,
            )
            update_sheet(save_df, "상세일정")
            st.success("확정 상태가 저장되었습니다!")
            st.rerun()
    else:
        st.write("구글 시트 '상세일정' 탭에 데이터를 입력해 주세요.")
