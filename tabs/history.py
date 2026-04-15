import streamlit as st
import pandas as pd
from datetime import datetime

from utils.sheets import update_sheet, VND_TO_KRW

# 여행 일정 날짜 매핑
TRIP_DAYS = [
    ("2026-05-30", "1일차(5/30)"),
    ("2026-05-31", "2일차(5/31)"),
    ("2026-06-01", "3일차(6/1)"),
    ("2026-06-02", "4일차(6/2)"),
    ("2026-06-03", "5일차(6/3)"),
]
TRIP_DATES = {d for d, _ in TRIP_DAYS}


def render(data: dict) -> None:
    st.header("📊 여행 경비내역")

    df_all = pd.DataFrame(data.get("expenses", []))
    if df_all.empty:
        st.info("아직 입력된 경비가 없습니다.")
        return

    # 실제 돈 쓴 순서 (날짜·시간 오름차순) — 시간 문자열 비교 오류 방지를 위해 datetime 파싱
    df_all["_dt"] = pd.to_datetime(
        df_all["날짜"].astype(str) + " " + df_all["시간"].astype(str),
        errors="coerce",
    )
    df_all = df_all.sort_values(by="_dt", ascending=True).drop(columns=["_dt"])
    df_all = df_all.reset_index(drop=True)

    # ── 일차 필터 버튼 ──────────────────────────────────────────────────────
    if "hist_filter" not in st.session_state:
        st.session_state.hist_filter = "전체"

    btn_labels = [label for _, label in TRIP_DAYS] + ["선구매", "전체"]
    btn_cols = st.columns(len(btn_labels))
    for col, label in zip(btn_cols, btn_labels):
        with col:
            is_active = st.session_state.hist_filter == label
            if st.button(label, use_container_width=True,
                         type="primary" if is_active else "secondary",
                         key=f"hist_btn_{label}"):
                st.session_state.hist_filter = label
                st.rerun()

    # ── 필터 적용 ────────────────────────────────────────────────────────────
    f = st.session_state.hist_filter
    if f == "전체":
        df_raw = df_all.copy()
    elif f == "선구매":
        df_raw = df_all[~df_all["날짜"].astype(str).isin(TRIP_DATES)].copy()
    else:
        # "1일차(5/30)" → 날짜 문자열 매핑
        date_str = next((d for d, label in TRIP_DAYS if label == f), None)
        df_raw = df_all[df_all["날짜"].astype(str) == date_str].copy() if date_str else df_all.copy()

    df_raw = df_raw.reset_index(drop=True)

    if df_raw.empty:
        st.info(f"**{f}** 경비 내역이 없습니다.")
        return

    # ── 합계 표시 ────────────────────────────────────────────────────────────
    total_vnd = pd.to_numeric(df_raw["총액(VND)"], errors="coerce").sum() if "총액(VND)" in df_raw.columns else 0
    total_krw = pd.to_numeric(df_raw["환산금액(KRW)"], errors="coerce").sum() if "환산금액(KRW)" in df_raw.columns else 0
    st.markdown(
        f"<div style='background:#f0f2f6;padding:10px 14px;border-radius:8px;"
        f"border-left:5px solid #FF4B4B;margin-bottom:16px;'>"
        f"<span style='font-size:0.85rem;color:#555;'><b>💰 {f} 합계</b></span><br>"
        f"<span style='font-size:1.2rem;color:#FF4B4B;'><b>{total_vnd:,.0f} VND</b></span>"
        f"<span style='font-size:0.9rem;color:#666;'> | 약 {total_krw:,.0f}원</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── 그룹 수집 ────────────────────────────────────────────────────────────
    if "h_edit_idx" not in st.session_state:
        st.session_state.h_edit_idx = None
    if "h_edit_memo_gkey" not in st.session_state:
        st.session_state.h_edit_memo_gkey = None
    if "h_add_row_gkey" not in st.session_state:
        st.session_state.h_add_row_gkey = None

    has_rid = "영수증ID" in df_raw.columns
    group_keys = []
    for i, row in df_raw.iterrows():
        rid = str(row.get("영수증ID", "") or "").strip() if has_rid else ""
        key = rid if rid and rid.lower() != "nan" else f"_hsolo_{i}"
        df_raw.at[i, "_gkey"] = key
        if key not in group_keys:
            group_keys.append(key)

    # ── 그룹 렌더링 ──────────────────────────────────────────────────────────
    for gkey in group_keys:
        g = df_raw[df_raw["_gkey"] == gkey]
        first = g.iloc[0]

        place  = str(first.get("장소명", "") or "").strip()
        date_s = str(first.get("날짜",   "") or "").strip()
        time_s = str(first.get("시간",   "") or "").strip()
        method = str(first.get("결제수단","") or "").strip()
        memo   = str(first.get("memo",   "") or "").strip()
        memo   = "" if memo.lower() == "nan" else memo
        is_group = not gkey.startswith("_hsolo_")

        try:
            grp_total = int(pd.to_numeric(g["총액(VND)"], errors="coerce").sum())
        except Exception:
            grp_total = 0

        with st.container(border=True):
            tag = f"<small style='color:#aaa;'>{gkey}</small>" if is_group else "<small style='color:#aaa;'>직접입력</small>"
            st.markdown(
                f"**📍 {place}** &nbsp; <small style='color:#888;'>{date_s} {time_s} | {method}</small> &nbsp; {tag}",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<p style='color:#FF4B4B;margin:2px 0 6px;'>합계 <b>{grp_total:,}</b> VND"
                f"&nbsp;<span style='font-size:0.8rem;color:#888;'>≈ {int(grp_total * VND_TO_KRW):,}원</span></p>",
                unsafe_allow_html=True,
            )

            # 품목 행
            for idx in g.index:
                row = df_raw.loc[idx]
                item_name = str(row.get("품목", "") or "").strip()
                try:
                    unit = int(float(str(row.get("단가", 0) or 0).replace(",", "")))
                except Exception:
                    unit = 0
                try:
                    qty = int(float(str(row.get("수량", 1) or 1)))
                except Exception:
                    qty = 1
                try:
                    total = int(float(str(row.get("총액(VND)", 0) or 0).replace(",", "")))
                except Exception:
                    total = 0

                if st.session_state.h_edit_idx == idx:
                    with st.form(f"h_edit_form_{idx}"):
                        ec1, ec2, ec3 = st.columns([3, 2, 1])
                        with ec1:
                            new_name  = st.text_input("품목", value=item_name)
                        with ec2:
                            new_price = st.number_input("단가(VND)", value=unit, min_value=0, step=100)
                        with ec3:
                            new_qty   = st.number_input("수량", value=max(qty, 1), min_value=1, step=1)
                        fc1, fc2 = st.columns(2)
                        with fc1:
                            if st.form_submit_button("✅ 저장", use_container_width=True):
                                df_raw.at[idx, "품목"]          = new_name
                                df_raw.at[idx, "단가"]          = new_price
                                df_raw.at[idx, "수량"]          = new_qty
                                df_raw.at[idx, "총액(VND)"]     = new_price * new_qty
                                df_raw.at[idx, "환산금액(KRW)"] = int(new_price * new_qty * VND_TO_KRW)
                                update_sheet(df_raw.drop(columns=["_gkey"]), "expenses")
                                st.session_state.h_edit_idx = None
                                st.rerun()
                        with fc2:
                            if st.form_submit_button("✖ 취소", use_container_width=True):
                                st.session_state.h_edit_idx = None
                                st.rerun()
                else:
                    if unit and qty:
                        st.markdown(
                            f"<p style='margin:3px 0;'>{item_name}"
                            f"&nbsp;<small style='color:#888;'>{unit:,} × {qty} = {total:,} VND</small></p>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f"<p style='margin:3px 0;'>{item_name}"
                            f"&nbsp;<small style='color:#888;'>{total:,} VND</small></p>",
                            unsafe_allow_html=True,
                        )
                    ic1, ic2 = st.columns(2)
                    with ic1:
                        if st.button("✏️ 수정", key=f"h_edit_{idx}", use_container_width=True):
                            st.session_state.h_edit_idx = idx
                            st.rerun()
                    with ic2:
                        if st.button("🗑️ 삭제", key=f"h_del_{idx}", use_container_width=True):
                            df_save = df_raw.drop(index=idx).drop(columns=["_gkey"])
                            update_sheet(df_save, "expenses")
                            st.rerun()

            # 메모
            if st.session_state.h_edit_memo_gkey == gkey:
                with st.form(f"h_memo_form_{gkey}"):
                    new_memo = st.text_area("메모", value=memo)
                    mc1, mc2 = st.columns(2)
                    with mc1:
                        if st.form_submit_button("✅ 저장", use_container_width=True):
                            for idx in g.index:
                                df_raw.at[idx, "memo"] = new_memo
                            update_sheet(df_raw.drop(columns=["_gkey"]), "expenses")
                            st.session_state.h_edit_memo_gkey = None
                            st.rerun()
                    with mc2:
                        if st.form_submit_button("✖ 취소", use_container_width=True):
                            st.session_state.h_edit_memo_gkey = None
                            st.rerun()
            else:
                mc1, mc2 = st.columns([6, 1])
                with mc1:
                    if memo:
                        st.caption(f"📝 {memo}")
                with mc2:
                    if st.button("✏️ 메모", key=f"h_memo_{gkey}", use_container_width=True):
                        st.session_state.h_edit_memo_gkey = gkey
                        st.rerun()
