import streamlit as st
import pandas as pd
from PIL import Image
from datetime import datetime

# 분리된 로직 임포트
from utils.sheets import update_sheet, VND_TO_KRW
from utils.ocr import parse_receipt

def render(data: dict) -> None:
    st.header("💰 경비 관리")
    
    # 1. 초기화 및 연동 (지도 핀에서 넘어온 경우 등)
    q_params = st.query_params
    prefilled_place = q_params.get("place", "")
    
    if "ocr_result" not in st.session_state:
        st.session_state.ocr_result = {}
    if "receipt_image" not in st.session_state:
        st.session_state.receipt_image = None

    # 2. 상단 지출 요약
    _render_summary(data)

    # 3. 입력 탭
    tab_manual, tab_ocr = st.tabs(["✍️ 직접 입력", "📸 영수증 OCR"])

    with tab_manual:
        _render_manual_form(data, prefilled_place)

    with tab_ocr:
        _render_ocr_form(data)

    # 4. 하단 지출 내역 목록
    st.divider()
    _render_expense_list(data)

def _render_summary(data: dict) -> None:
    df_exp = pd.DataFrame(data.get("expenses", []))
    if not df_exp.empty:
        # 컬럼이 있는지 확인하고 합계 계산 (없으면 0)
        total_vnd = pd.to_numeric(df_exp["총액(VND)"], errors='coerce').sum() if "총액(VND)" in df_exp.columns else 0
        total_krw = pd.to_numeric(df_exp["환산금액(KRW)"], errors='coerce').sum() if "환산금액(KRW)" in df_exp.columns else 0
        
        st.markdown(f"""
        <div style='background-color: #f0f2f6; padding: 12px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid #FF4B4B;'>
            <p style='margin: 0; font-size: 0.9rem; color: #555;'><b>💰 누적 지출 합계</b></p>
            <p style='margin: 0; font-size: 1.3rem; color: #FF4B4B;'>
                <b>{total_vnd:,.0f} VND</b> <span style='font-size: 1rem; color: #666;'>| 약 {total_krw:,.0f}원</span>
            </p>
        </div>
        """, unsafe_allow_html=True)

def _render_manual_form(data: dict, prefilled_place: str) -> None:
    if "manual_form_key" not in st.session_state:
        st.session_state.manual_form_key = 0

    # memo_key에 form_key 포함 → 저장 후 자동으로 새 키 = 기본값으로 초기화
    memo_key = f"manual_memo_{st.session_state.manual_form_key}"
    default_memo = f"[{prefilled_place}]\n" if prefilled_place else ""
    if memo_key not in st.session_state:
        st.session_state[memo_key] = default_memo

    def _clear_memo():
        st.session_state[memo_key] = ""

    # 메모 삭제: 폼 바깥 버튼 + on_click → 폼 submit 없이 메모만 초기화
    st.button("🗑️ 메모 삭제", on_click=_clear_memo,
              key=f"clear_memo_btn_{st.session_state.manual_form_key}")

    with st.form(f"manual_expense_form_{st.session_state.manual_form_key}"):
        col1, col2 = st.columns(2)
        with col1:
            exp_date = st.date_input("날짜", datetime.now())
            exp_time = st.text_input("시간", datetime.now().strftime("%H:%M"))
        with col2:
            exp_place = st.text_input("장소명", value=prefilled_place)
            exp_method = st.selectbox("결제수단", ["현금", "카드"])

        exp_items = st.text_input("품목 (식비, 쇼핑 등)")

        col3, col4 = st.columns(2)
        with col3:
            exp_vnd = st.number_input("금액 (VND)", min_value=0, step=1000)
        with col4:
            exp_krw = int(exp_vnd * VND_TO_KRW)
            st.text_input("환산금액 (KRW)", value=f"{exp_krw:,}원", disabled=True)

        # key로 관리 → on_click 콜백이 직접 세션 값을 바꿔 즉시 반영
        exp_memo = st.text_area("메모", key=memo_key)

        if st.form_submit_button("💾 저장하기", use_container_width=True):
            if not exp_items.strip() and exp_vnd == 0:
                st.warning("품목 또는 금액을 입력해주세요.")
            else:
                st.session_state.manual_form_key += 1  # 폼 초기화 (memo_key도 무효화)
                new_row = {
                    "날짜": exp_date.strftime("%Y-%m-%d"),
                    "시간": exp_time,
                    "장소명": exp_place,
                    "품목": exp_items,
                    "단가": "", "수량": "",
                    "총액(VND)": exp_vnd, "환산금액(KRW)": exp_krw,
                    "결제수단": exp_method, "memo": exp_memo,
                    "영수증URL": ""
                }
                _save_and_rerun(new_row, data)

def _render_ocr_form(data: dict) -> None:
    # 파일 업로더 리셋용 키 카운터
    if "ocr_upload_key" not in st.session_state:
        st.session_state.ocr_upload_key = 0
    # 메모 textarea key 세대 카운터 (저장 시 +1 → 새 키로 초기화)
    if "ocr_memo_gen" not in st.session_state:
        st.session_state.ocr_memo_gen = 0

    gen = st.session_state.ocr_memo_gen
    ocr_memo_skey = f"ocr_memo_{gen}"

    def _clear_ocr_memo():
        st.session_state[ocr_memo_skey] = ""

    uploaded_file = st.file_uploader(
        "영수증 사진 업로드", type=["jpg", "jpeg", "png"],
        key=f"ocr_file_{st.session_state.ocr_upload_key}"
    )

    if uploaded_file:
        st.session_state.receipt_image = uploaded_file
        img = Image.open(uploaded_file)
        st.image(img, caption="업로드된 영수증", use_container_width=True)

        if st.button("🔍 영수증 분석하기", use_container_width=True):
            with st.spinner("AI가 영수증을 분석 중입니다..."):
                result = parse_receipt(img)
                if result:
                    st.session_state.ocr_result = result
                    # OCR 완료 시점에 store_name으로 메모 기본값 설정
                    store_name = result.get("store_name", "")
                    st.session_state[ocr_memo_skey] = f"[{store_name}] OCR 인식" if store_name else "OCR 인식"
                    st.success("분석 완료! 아래 내용을 확인하고 저장하세요.")

    if st.session_state.ocr_result:
        res = st.session_state.ocr_result

        # st.form 없이 일반 위젯 사용 — 저장·삭제 버튼을 같은 줄에 배치하기 위함
        col1, col2 = st.columns(2)
        with col1:
            o_date = st.text_input("날짜", key=f"ocr_date_{gen}",
                                   value=res.get("date", datetime.now().strftime("%Y-%m-%d")))
            o_time = st.text_input("시간", key=f"ocr_time_{gen}",
                                   value=res.get("time", ""))
        with col2:
            o_place = st.text_input("장소명", key=f"ocr_place_{gen}",
                                    value=res.get("store_name", ""))
            o_method = st.selectbox("결제수단", ["현금", "카드"],
                                    key=f"ocr_method_{gen}",
                                    index=0 if res.get("payment_method", "").lower() != "card" else 1)

        st.markdown("**품목 목록 (수정 가능)**")
        raw_items = res.get("items", [])
        if not isinstance(raw_items, list):
            raw_items = []
        items_df = pd.DataFrame(
            [{"품목": it.get("name", ""), "단가(VND)": it.get("unit_price", 0), "수량": it.get("quantity", 1)} for it in raw_items]
        ) if raw_items else pd.DataFrame({"품목": [""], "단가(VND)": [0], "수량": [1]})
        edited_df = st.data_editor(items_df, num_rows="dynamic",
                                   key=f"ocr_items_{gen}",
                                   use_container_width=True)

        # 합계 비교
        try:
            calc_total = int(sum(
                it.get("unit_price", 0) * it.get("quantity", 1) for it in raw_items
            ))
        except:
            calc_total = 0
        try:
            receipt_total = int(res.get("receipt_total", 0) or 0)
        except:
            receipt_total = 0

        if receipt_total and calc_total != receipt_total:
            st.markdown(
                f"<div style='background:#fff3cd;border-left:4px solid #ffc107;padding:8px 12px;border-radius:4px;margin:4px 0;'>"
                f"⚠️ 품목 합계 <b>{calc_total:,}</b> VND &nbsp;≠&nbsp; 영수증 합계 <b>{receipt_total:,}</b> VND"
                f"<br><small style='color:#856404;'>품목 금액을 확인하고 수정해 주세요.</small></div>",
                unsafe_allow_html=True,
            )
        elif receipt_total and calc_total == receipt_total:
            st.markdown(
                f"<div style='background:#d4edda;border-left:4px solid #28a745;padding:8px 12px;border-radius:4px;margin:4px 0;'>"
                f"✅ 품목 합계 <b>{calc_total:,}</b> VND = 영수증 합계 <b>{receipt_total:,}</b> VND</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div style='background:#f8f9fa;border-left:4px solid #aaa;padding:8px 12px;border-radius:4px;margin:4px 0;'>"
                f"합계 <b>{calc_total:,}</b> VND</div>",
                unsafe_allow_html=True,
            )

        o_memo = st.text_area("메모", key=ocr_memo_skey)

        # 저장(70%) + 메모 삭제(30%) 같은 줄 배치
        bc1, bc2 = st.columns([7, 3])
        with bc1:
            save_ocr = st.button("💾 품목별 저장하기", use_container_width=True, type="primary")
        with bc2:
            st.button("🗑️ 메모 삭제", on_click=_clear_ocr_memo,
                      key=f"ocr_clear_btn_{gen}", use_container_width=True)

        if save_ocr:
            receipt_id = datetime.now().strftime("RCP_%m%d_%H%M%S")
            new_rows = []
            for _, item_row in edited_df.iterrows():
                name = str(item_row.get("품목", "")).strip()
                if not name:
                    continue
                try:
                    unit_price = int(float(str(item_row.get("단가(VND)", 0)).replace(",", "")))
                except:
                    unit_price = 0
                try:
                    qty = int(item_row.get("수량", 1))
                except:
                    qty = 1
                total_vnd = unit_price * qty
                new_rows.append({
                    "영수증ID": receipt_id,
                    "날짜": o_date, "시간": o_time, "장소명": o_place,
                    "품목": name, "단가": unit_price, "수량": qty,
                    "총액(VND)": total_vnd, "환산금액(KRW)": int(total_vnd * VND_TO_KRW),
                    "결제수단": o_method, "memo": o_memo, "영수증URL": ""
                })
            if new_rows:
                df_exp = pd.DataFrame(data.get("expenses", []))
                df_final = pd.concat([df_exp, pd.DataFrame(new_rows)], ignore_index=True)
                st.session_state.ocr_result = {}
                st.session_state.receipt_image = None
                st.session_state.ocr_upload_key += 1  # 파일 업로더 리셋
                st.session_state.ocr_memo_gen += 1    # 메모 key 세대 올려서 초기화
                update_sheet(df_final, "expenses")
                st.toast(f"✅ {len(new_rows)}개 품목 저장 완료!")
                st.rerun()

def _render_expense_list(data: dict) -> None:
    st.subheader("📊 여행 경비 내역")
    df_raw = pd.DataFrame(data.get("expenses", []))

    if df_raw.empty:
        st.info("아직 입력된 경비가 없습니다. 위 폼에서 경비를 추가해 보세요!")
        return

    # 날짜/시간 최신순 정렬 후 인덱스 재설정
    sort_cols = [c for c in ["날짜", "시간"] if c in df_raw.columns]
    if sort_cols:
        df_raw = df_raw.sort_values(by=sort_cols, ascending=False)
    df_raw = df_raw.reset_index(drop=True)

    if "edit_idx" not in st.session_state:
        st.session_state.edit_idx = None
    if "edit_memo_gkey" not in st.session_state:
        st.session_state.edit_memo_gkey = None
    if "add_row_gkey" not in st.session_state:
        st.session_state.add_row_gkey = None

    # 영수증ID 기준 그룹 순서 수집
    has_rid = "영수증ID" in df_raw.columns
    group_keys = []
    for i, row in df_raw.iterrows():
        rid = str(row.get("영수증ID", "") or "").strip() if has_rid else ""
        key = rid if rid and rid.lower() != "nan" else f"_solo_{i}"
        df_raw.at[i, "_gkey"] = key
        if key not in group_keys:
            group_keys.append(key)

    for gkey in group_keys:
        g = df_raw[df_raw["_gkey"] == gkey]
        first = g.iloc[0]

        place   = str(first.get("장소명", "") or "").strip()
        date_s  = str(first.get("날짜",   "") or "").strip()
        time_s  = str(first.get("시간",   "") or "").strip()
        method  = str(first.get("결제수단","") or "").strip()
        memo    = str(first.get("memo",   "") or "").strip()
        memo    = "" if memo.lower() == "nan" else memo
        is_group = not gkey.startswith("_solo_")

        try:
            grp_total = int(pd.to_numeric(g["총액(VND)"], errors="coerce").sum())
        except:
            grp_total = 0

        with st.container(border=True):
            # ── 그룹 헤더 ──
            tag = f"<small style='color:#aaa;'>{gkey}</small>" if is_group else "<small style='color:#aaa;'>직접입력</small>"
            st.markdown(
                f"**📍 {place}** &nbsp; <small style='color:#888;'>{date_s} {time_s} | {method}</small> &nbsp; {tag}",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<p style='color:#FF4B4B; margin:2px 0 6px;'>합계 <b>{grp_total:,}</b> VND"
                f"&nbsp;<span style='font-size:0.8rem; color:#888;'>≈ {int(grp_total * VND_TO_KRW):,}원</span></p>",
                unsafe_allow_html=True,
            )

            # ── 품목 행 ──
            for idx in g.index:
                row = df_raw.loc[idx]
                item_name = str(row.get("품목", "") or "").strip()
                try:
                    unit  = int(float(str(row.get("단가", 0) or 0).replace(",", "")))
                except:
                    unit  = 0
                try:
                    qty   = int(float(str(row.get("수량", 1) or 1)))
                except:
                    qty   = 1
                try:
                    total = int(float(str(row.get("총액(VND)", 0) or 0).replace(",", "")))
                except:
                    total = 0

                if st.session_state.edit_idx == idx:
                    # ── 인라인 편집 폼 ──
                    with st.form(f"edit_form_{idx}"):
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
                                df_raw.at[idx, "품목"]        = new_name
                                df_raw.at[idx, "단가"]        = new_price
                                df_raw.at[idx, "수량"]        = new_qty
                                df_raw.at[idx, "총액(VND)"]   = new_price * new_qty
                                df_raw.at[idx, "환산금액(KRW)"] = int(new_price * new_qty * VND_TO_KRW)
                                update_sheet(df_raw.drop(columns=["_gkey"]), "expenses")
                                st.session_state.edit_idx = None
                                st.rerun()
                        with fc2:
                            if st.form_submit_button("✖ 취소", use_container_width=True):
                                st.session_state.edit_idx = None
                                st.rerun()
                else:
                    # ── 일반 표시 ──
                    ic1, ic2, ic3 = st.columns([5, 1, 1])
                    with ic1:
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
                    with ic2:
                        if st.button("✏️", key=f"edit_{idx}", use_container_width=True):
                            st.session_state.edit_idx = idx
                            st.rerun()
                    with ic3:
                        if st.button("🗑️", key=f"del_{idx}", use_container_width=True):
                            df_save = df_raw.drop(index=idx).drop(columns=["_gkey"])
                            update_sheet(df_save, "expenses")
                            st.rerun()

            # ── 메모 (그룹 단위 편집) ──
            if st.session_state.edit_memo_gkey == gkey:
                with st.form(f"memo_form_{gkey}"):
                    new_memo = st.text_area("메모", value=memo)
                    mc1, mc2 = st.columns(2)
                    with mc1:
                        if st.form_submit_button("✅ 저장", use_container_width=True):
                            for idx in g.index:
                                df_raw.at[idx, "memo"] = new_memo
                            update_sheet(df_raw.drop(columns=["_gkey"]), "expenses")
                            st.session_state.edit_memo_gkey = None
                            st.rerun()
                    with mc2:
                        if st.form_submit_button("✖ 취소", use_container_width=True):
                            st.session_state.edit_memo_gkey = None
                            st.rerun()
            else:
                mc1, mc2 = st.columns([6, 1])
                with mc1:
                    if memo:
                        st.caption(f"📝 {memo}")
                with mc2:
                    if st.button("✏️ 메모", key=f"memo_{gkey}", use_container_width=True):
                        st.session_state.edit_memo_gkey = gkey
                        st.rerun()

            # ── 행 추가 ──
            if st.session_state.add_row_gkey == gkey:
                with st.form(f"add_row_form_{gkey}"):
                    st.markdown("**+ 품목 추가**")
                    ac1, ac2, ac3 = st.columns([3, 2, 1])
                    with ac1:
                        add_name  = st.text_input("품목", key=f"an_{gkey}")
                    with ac2:
                        add_price = st.number_input("단가(VND)", min_value=0, step=100, key=f"ap_{gkey}")
                    with ac3:
                        add_qty   = st.number_input("수량", min_value=1, step=1, value=1, key=f"aq_{gkey}")
                    fc1, fc2 = st.columns(2)
                    with fc1:
                        if st.form_submit_button("✅ 추가", use_container_width=True):
                            # solo 그룹이면 영수증ID 신규 부여 후 기존 행에도 적용
                            if gkey.startswith("_solo_"):
                                new_rid = datetime.now().strftime("RCP_%m%d_%H%M%S")
                                for i in g.index:
                                    df_raw.at[i, "영수증ID"] = new_rid
                                group_id = new_rid
                            else:
                                group_id = gkey

                            total_vnd = add_price * add_qty
                            new_row = {
                                "영수증ID": group_id,
                                "날짜": date_s, "시간": time_s, "장소명": place,
                                "품목": add_name, "단가": add_price, "수량": add_qty,
                                "총액(VND)": total_vnd,
                                "환산금액(KRW)": int(total_vnd * VND_TO_KRW),
                                "결제수단": method, "memo": memo, "영수증URL": "",
                            }
                            df_save = pd.concat(
                                [df_raw.drop(columns=["_gkey"]), pd.DataFrame([new_row])],
                                ignore_index=True,
                            )
                            update_sheet(df_save, "expenses")
                            st.session_state.add_row_gkey = None
                            st.rerun()
                    with fc2:
                        if st.form_submit_button("✖ 취소", use_container_width=True):
                            st.session_state.add_row_gkey = None
                            st.rerun()
            else:
                if st.button("➕ 품목 추가", key=f"addrow_{gkey}", use_container_width=True):
                    st.session_state.add_row_gkey = gkey
                    st.rerun()

def _save_and_rerun(new_row: dict, data: dict) -> None:
    """공통 저장 로직 — 즉시 로컬 반영 후 대기열 적재"""
    df_exp = pd.DataFrame(data.get("expenses", []))
    df_new = pd.DataFrame([new_row])
    df_final = pd.concat([df_exp, df_new], ignore_index=True)
    update_sheet(df_final, "expenses")
    st.toast("✅ 저장 완료!")
    st.rerun()
