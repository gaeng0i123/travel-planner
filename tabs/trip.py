import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import folium
from streamlit_folium import st_folium


TRIP_DAYS = [
    ("5/30", "1일차(5/30,토)"),
    ("5/31", "2일차(5/31,일)"),
    ("6/1",  "3일차(6/1,월)"),
    ("6/2",  "4일차(6/2,화)"),
    ("6/3",  "5일차(6/3,수)"),
]

CATEGORY_ICON = {"에어컨카페": "☕", "스파": "💆", "식당": "🍽️"}

_SCROLL_JS = """
<script>
(function() {
    var doc = window.parent.document;
    var main = doc.querySelector('[data-testid="stMain"]');
    var lastOurScroll = 0, debounce;

    function applyScroll() {
        var anchor = doc.getElementById('trip-map-anchor');
        if (!anchor) return;
        var cTop = main ? main.getBoundingClientRect().top : 0;
        lastOurScroll = Date.now();
        anchor.scrollIntoView({behavior: 'instant', block: 'start'});
        var aTop = anchor.getBoundingClientRect().top;
        if (Math.abs(aTop - cTop) > 5 && main) main.scrollTop += (aTop - cTop);
    }

    var safetyTimer = setTimeout(applyScroll, 900);

    function onScroll() {
        if (Date.now() - lastOurScroll < 400) return;
        clearTimeout(debounce);
        debounce = setTimeout(function() {
            clearTimeout(safetyTimer);
            applyScroll();
        }, 80);
    }
    var target = main || window.parent;
    target.addEventListener('scroll', onScroll);
    setTimeout(function(){ target.removeEventListener('scroll', onScroll); }, 5000);
})();
</script>
"""


def _val(v) -> str:
    return "" if pd.isna(v) or str(v).strip() == "" else str(v).strip()


def _collect_pins(df_day: pd.DataFrame) -> list:
    """확정 일정 DataFrame → 핀 목록 [(lat, lon, num, time, content, place, gmap_url)]."""
    pins = []
    if df_day.empty or "lat" not in df_day.columns:
        return pins
    coord_count: dict = {}
    for i, row in df_day.iterrows():
        if (pd.notna(row.get("lat")) and pd.notna(row.get("lon"))
                and row.get("lat") != "" and row.get("lon") != ""):
            lat, lon = float(row["lat"]), float(row["lon"])
            key   = (lat, lon)
            count = coord_count.get(key, 0)
            coord_count[key] = count + 1
            offset  = 0.00015
            offsets = [
                (0, 0), (offset, 0), (-offset, 0),
                (0, offset), (0, -offset),
                (offset, offset), (-offset, -offset),
            ]
            if count < len(offsets):
                lat += offsets[count][0]
                lon += offsets[count][1]
            pins.append((
                lat, lon, i + 1,
                row.get("시간", ""), row.get("내용", ""),
                row.get("장소명", ""), row.get("구글지도", ""),
            ))
    return pins


# ── 렌더 함수 ──────────────────────────────────────────────────────────────────

def render(data: dict) -> None:
    st.header("🛵 현지 실시간 관리")

    # 확정 일정 필터링
    confirmed = [
        r for r in data["itinerary"]
        if str(r.get("확정", "")).strip().lower() in ("true", "1", "yes", "확정", "ok")
        and str(r.get("내용", "")).strip()
        and str(r.get("날짜", "")).strip()
    ]
    df_confirmed = pd.DataFrame(confirmed) if confirmed else pd.DataFrame()

    # memo 장소 필터링 (확정=memo, 날짜에 카테고리명, 좌표 있는 것만)
    memo_places = [
        r for r in data["itinerary"]
        if str(r.get("확정", "")).strip().lower() == "memo"
        and str(r.get("lat", "")).strip() not in ("", "nan")
        and str(r.get("lon", "")).strip() not in ("", "nan")
    ]

    # 카테고리 목록 (날짜 칸 기준, 시트 순서 유지)
    categories: list[str] = []
    for r in memo_places:
        cat = str(r.get("날짜", "")).strip()
        if cat and cat not in categories:
            categories.append(cat)

    if df_confirmed.empty and not memo_places:
        st.info("여행 준비 탭 예상일정에서 일정을 확정하면 여기에 표시됩니다.")
        return

    # 세션 상태 초기화
    if "view_mode" not in st.session_state:
        st.session_state.view_mode = "day"
    if "selected_day" not in st.session_state:
        st.session_state.selected_day = 0
    if "memo_category" not in st.session_state or st.session_state.memo_category not in categories:
        st.session_state.memo_category = categories[0] if categories else ""

    # ── 1행: 일차 버튼 ────────────────────────────────────────────────────────
    day_cols = st.columns(len(TRIP_DAYS))
    for i, (col, (_, label)) in enumerate(zip(day_cols, TRIP_DAYS)):
        with col:
            is_active = (st.session_state.view_mode == "day"
                         and st.session_state.selected_day == i)
            if st.button(label, use_container_width=True,
                         type="primary" if is_active else "secondary",
                         key=f"day_{i}"):
                st.session_state.view_mode  = "day"
                st.session_state.selected_day = i
                st.session_state.pop("map_center", None)
                st.session_state.pop("map_zoom", None)
                st.rerun()

    # ── 2행: 카테고리 버튼 ────────────────────────────────────────────────────
    btn2_labels = [(cat, CATEGORY_ICON.get(cat, "📌"), "memo") for cat in categories]
    btn2_labels.append(("전체동선", "🗺️", "all"))
    btn2_cols = st.columns(len(btn2_labels))
    for ci, (col, (cat, icon, mode)) in enumerate(zip(btn2_cols, btn2_labels)):
        with col:
            if mode == "memo":
                is_active = (st.session_state.view_mode == "memo"
                             and st.session_state.memo_category == cat)
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

    # ── 콘텐츠 영역 ───────────────────────────────────────────────────────────
    if st.session_state.view_mode == "day":
        _render_day(df_confirmed, memo_places)
    elif st.session_state.view_mode == "memo" and st.session_state.memo_category:
        _render_memo(memo_places)
    elif st.session_state.view_mode == "all":
        _render_all(df_confirmed)


def _render_day(df_confirmed: pd.DataFrame, memo_places: list) -> None:
    if st.session_state.selected_day >= len(TRIP_DAYS):
        st.session_state.selected_day = 0

    selected_date, selected_label = TRIP_DAYS[st.session_state.selected_day]
    df_day = (
        df_confirmed[df_confirmed["날짜"] == selected_date].reset_index(drop=True)
        if not df_confirmed.empty else pd.DataFrame()
    )

    st.markdown('<div id="trip-map-anchor"></div>', unsafe_allow_html=True)

    if st.session_state.get("scroll_to_map"):
        st.session_state.scroll_to_map = False
        components.html(_SCROLL_JS, height=1)

    st.caption(f"📅 {selected_label} — 확정 {len(df_day)}개")

    # 지도
    map_center = st.session_state.get("map_center", [16.047079, 108.206230])
    map_zoom   = st.session_state.get("map_zoom", 13)
    m = folium.Map(location=map_center, zoom_start=map_zoom)

    pins = _collect_pins(df_day)

    if len(pins) >= 2:
        folium.PolyLine(
            locations=[(p[0], p[1]) for p in pins],
            color="#FF4B4B", weight=2.5, opacity=0.7, dash_array="6",
        ).add_to(m)

    for lat, lon, num, time_val, content, place, gmap_url in pins:
        gmap_link  = gmap_url or f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
        # 경비 입력 탭으로 이동하는 링크 (쿼리 파라미터 활용)
        expense_link = f"/?tab=expenses&place={place or content}"
        popup_html = (
            f"<b>{num}. {place or content}</b><br>{time_val}"
            f"<br><a href='{gmap_link}' target='_blank' style='color:#4A90D9;'>🗺️ 구글맵으로 보기</a>"
            f"<br><a href='javascript:void(0)' onclick=\"window.top.location.href=window.top.location.origin+'{expense_link}'\" style='color:#FF4B4B; font-weight:bold;'>💰 경비 기록하기</a>"
        )
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=f"{num}. {place or content}",
            icon=folium.DivIcon(
                html=(f'<div style="background:#FF4B4B;color:white;border-radius:50%;'
                      f'width:28px;height:28px;display:flex;align-items:center;'
                      f'justify-content:center;font-weight:bold;font-size:14px;'
                      f'box-shadow:0 2px 4px rgba(0,0,0,0.3);">{num}</div>'),
                icon_size=(28, 28), icon_anchor=(14, 14),
            ),
        ).add_to(m)

    # memo 핀 (파란 📌)
    for r in memo_places:
        try:
            mlat, mlon = float(r["lat"]), float(r["lon"])
            mplace = str(r.get("장소명", "") or r.get("내용", "")).strip()
            mmemo  = str(r.get("메모", "")).strip()
            mgmap  = str(r.get("구글지도", "")
                         or f"https://www.google.com/maps/search/?api=1&query={mlat},{mlon}")
            # 경비 입력 탭으로 이동하는 링크
            expense_link = f"/?tab=expenses&place={mplace}"
            popup_html = (
                f"<b>📌 {mplace}</b>" + (f"<br>{mmemo}" if mmemo else "")
                + f"<br><a href='{mgmap}' target='_blank' style='color:#4A90D9;'>🗺️ 구글맵으로 보기</a>"
                + f"<br><a href='javascript:void(0)' onclick=\"window.top.location.href=window.top.location.origin+'{expense_link}'\" style='color:#FF4B4B; font-weight:bold;'>💰 경비 기록하기</a>"
            )
            folium.Marker(
                location=[mlat, mlon],
                popup=folium.Popup(popup_html, max_width=220),
                tooltip=f"📌 {mplace}",
                icon=folium.DivIcon(
                    html=(f'<div style="background:#4A90D9;color:white;border-radius:50%;'
                          f'width:28px;height:28px;display:flex;align-items:center;'
                          f'justify-content:center;font-size:15px;'
                          f'box-shadow:0 2px 4px rgba(0,0,0,0.3);">📌</div>'),
                    icon_size=(28, 28), icon_anchor=(14, 14),
                ),
            ).add_to(m)
        except (ValueError, TypeError):
            pass

    map_key = f"day_map_{map_center[0]}_{map_center[1]}_{map_zoom}"
    st_folium(m, use_container_width=True, height=500, key=map_key)

    # 일정 목록
    st.subheader(f"📋 {selected_label} 확정 일정")

    for i, row in df_day.iterrows():
        duration_str      = _val(row.get("소요시간"))
        transport_str     = _val(row.get("이동시간"))
        duration_combined = (f"{duration_str}({transport_str})"
                             if duration_str and transport_str else duration_str or "")
        place   = _val(row.get("장소명"))
        lat_v   = _val(row.get("lat"))
        lon_v   = _val(row.get("lon"))
        time_v  = _val(row.get("시간"))
        content = _val(row.get("내용"))
        memo    = _val(row.get("메모"))

        row1_parts = [p for p in [time_v, content, duration_combined] if p]
        row1_text  = " - ".join(row1_parts) if row1_parts else ""
        st.markdown(
            f"<p style='font-size:13px;opacity:0.7;margin:8px 0 2px;'>"
            f"<b>{i + 1}.</b> {row1_text}</p>",
            unsafe_allow_html=True,
        )

        if place and lat_v and lon_v:
            if st.button(f"📍  {place}", key=f"place_{i}", use_container_width=True):
                st.session_state.map_center  = [float(lat_v), float(lon_v)]
                st.session_state.map_zoom    = 16
                st.session_state.scroll_to_map = True
                st.rerun()
        elif place:
            st.markdown(
                f"<p style='font-size:15px;font-weight:600;margin:2px 0;'>📍 {place}</p>",
                unsafe_allow_html=True,
            )

        if memo:
            st.markdown(
                f"<p style='font-size:12px;opacity:0.65;margin:2px 0 6px;"
                f"white-space:pre-wrap;'>{memo}</p>",
                unsafe_allow_html=True,
            )

        st.divider()


def _render_memo(memo_places: list) -> None:
    selected_memos = [
        r for r in memo_places
        if str(r.get("날짜", "")).strip() == st.session_state.memo_category
    ]
    icon = CATEGORY_ICON.get(st.session_state.memo_category, "📌")

    st.markdown('<div id="trip-map-anchor"></div>', unsafe_allow_html=True)

    if st.session_state.get("scroll_to_map"):
        st.session_state.scroll_to_map = False
        components.html(_SCROLL_JS, height=1)

    st.caption(f"{icon} {st.session_state.memo_category} — {len(selected_memos)}개")

    memo_map_center = st.session_state.get("map_center", [16.047079, 108.206230])
    memo_map_zoom   = st.session_state.get("map_zoom", 12)
    m = folium.Map(location=memo_map_center, zoom_start=memo_map_zoom)

    for idx, r in enumerate(selected_memos, start=1):
        try:
            mlat, mlon = float(r["lat"]), float(r["lon"])
            mplace = str(r.get("장소명", "") or "").strip()
            mmemo  = str(r.get("메모", "")).strip()
            mgmap  = str(r.get("구글지도", "")
                         or f"https://www.google.com/maps/search/?api=1&query={mlat},{mlon}")
            # 경비 입력 탭으로 이동하는 링크
            expense_link = f"/?tab=expenses&place={mplace}"
            popup_html = (
                f"<b>{idx}. {mplace}</b>" + (f"<br>{mmemo}" if mmemo else "")
                + f"<br><a href='{mgmap}' target='_blank' style='color:#4A90D9;'>🗺️ 구글맵으로 보기</a>"
                + f"<br><a href='javascript:void(0)' onclick=\"window.top.location.href=window.top.location.origin+'{expense_link}'\" style='color:#FF4B4B; font-weight:bold;'>💰 경비 기록하기</a>"
            )
            folium.Marker(
                location=[mlat, mlon],
                popup=folium.Popup(popup_html, max_width=220),
                tooltip=f"{idx}. {mplace}",
                icon=folium.DivIcon(
                    html=(f'<div style="background:#4A90D9;color:white;border-radius:50%;'
                          f'width:28px;height:28px;display:flex;align-items:center;'
                          f'justify-content:center;font-size:15px;'
                          f'box-shadow:0 2px 4px rgba(0,0,0,0.3);">📌</div>'),
                    icon_size=(28, 28), icon_anchor=(14, 14),
                ),
            ).add_to(m)
        except (ValueError, TypeError):
            pass

    memo_map_key = f"memo_map_{memo_map_center[0]}_{memo_map_center[1]}"
    st_folium(m, use_container_width=True, height=400, key=memo_map_key)

    for idx, r in enumerate(selected_memos):
        duration_str      = _val(r.get("소요시간"))
        transport_str     = _val(r.get("이동시간"))
        duration_combined = (f"{duration_str}({transport_str})"
                             if duration_str and transport_str else duration_str or "")
        time_v  = _val(r.get("시간"))
        content = _val(r.get("내용"))
        mplace  = _val(r.get("장소명"))
        mmemo   = _val(r.get("메모"))
        mlat    = _val(r.get("lat"))
        mlon    = _val(r.get("lon"))

        row1_parts = [p for p in [time_v, content, duration_combined] if p]
        row1_text  = " - ".join(row1_parts) if row1_parts else ""
        st.markdown(
            f"<p style='font-size:13px;opacity:0.7;margin:8px 0 2px;'>"
            f"<b>{idx + 1}.</b> {row1_text}</p>",
            unsafe_allow_html=True,
        )

        if mplace and mlat and mlon:
            if st.button(f"📌  {mplace}", key=f"memo_place_{idx}", use_container_width=True):
                st.session_state.map_center    = [float(mlat), float(mlon)]
                st.session_state.map_zoom      = 16
                st.session_state.scroll_to_map = True
                st.rerun()
        elif mplace:
            st.markdown(
                f"<p style='font-size:15px;font-weight:600;margin:2px 0;'>📌 {mplace}</p>",
                unsafe_allow_html=True,
            )

        if mmemo:
            st.markdown(
                f"<p style='font-size:12px;opacity:0.65;margin:2px 0 6px;"
                f"white-space:pre-wrap;'>{mmemo}</p>",
                unsafe_allow_html=True,
            )
        st.divider()


def _render_all(df_confirmed: pd.DataFrame) -> None:
    day_colors = ["#FF4B4B", "#FF8C00", "#2ECC71", "#9B59B6", "#1ABC9C"]
    st.caption("🗺️ 전체동선 — 5일 확정 일정")
    m = folium.Map(location=[16.047079, 108.206230], zoom_start=12)

    for day_idx, (date, label) in enumerate(TRIP_DAYS):
        color = day_colors[day_idx % len(day_colors)]
        df_d  = (
            df_confirmed[df_confirmed["날짜"] == date].reset_index(drop=True)
            if not df_confirmed.empty else pd.DataFrame()
        )
        if df_d.empty or "lat" not in df_d.columns:
            continue

        pins_d = _collect_pins(df_d)

        if len(pins_d) >= 2:
            folium.PolyLine(
                locations=[(p[0], p[1]) for p in pins_d],
                color=color, weight=2.5, opacity=0.8, dash_array="6",
                tooltip=label,
            ).add_to(m)

        for lat, lon, num, time_val, content, place, _ in pins_d:
            popup_html = f"<b>[{label}] {num}. {place or content}</b><br>{time_val}"
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=200),
                tooltip=f"[{label}] {num}. {place or content}",
                icon=folium.DivIcon(
                    html=(f'<div style="background:{color};color:white;border-radius:50%;'
                          f'width:26px;height:26px;display:flex;align-items:center;'
                          f'justify-content:center;font-weight:bold;font-size:12px;'
                          f'box-shadow:0 2px 4px rgba(0,0,0,0.3);">{num}</div>'),
                    icon_size=(26, 26), icon_anchor=(13, 13),
                ),
            ).add_to(m)

    st_folium(m, use_container_width=True, height=600)

    legend_html = "".join(
        f'<span style="display:inline-block;margin:4px 8px;font-size:13px;">'
        f'<span style="background:{day_colors[i % len(day_colors)]};color:white;'
        f'border-radius:50%;padding:2px 7px;font-weight:bold;">●</span> {label}'
        f'</span>'
        for i, (_, label) in enumerate(TRIP_DAYS)
    )
    st.markdown(legend_html, unsafe_allow_html=True)
