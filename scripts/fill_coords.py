"""
구글 시트 '상세일정' 탭에서 구글지도 링크만 있고 좌표(lat/lon)/장소명이 없는 행에
데이터를 자동으로 채워 넣는 스크립트.

채우는 항목:
  - lat, lon : 구글 지도 URL에서 좌표 추출
  - 장소명   : URL 리다이렉트 후 /place/NAME/ 파싱 (장소명 비어있을 때만)
  - open, close: 직접 입력 (자동화 불가)

사용법:
    python3 fill_coords.py
"""

import re
import time
import tomllib
import urllib.parse
import urllib.request
from pathlib import Path

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


# ── 설정 ──────────────────────────────────────────────────────────────────────

SECRETS_PATH   = Path(".streamlit/secrets.toml")
SHEET_ID       = "12j2JaYTvnNmSUwJJ8zSWUuqJh5MUUe5JwftYYrz_6oY"
WORKSHEET_NAME = "상세일정"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

COL_MAPS  = "구글지도"
COL_LAT   = "lat"
COL_LON   = "lon"
COL_PLACE = "장소명"


# ── 유틸리티 ──────────────────────────────────────────────────────────────────

def load_creds() -> Credentials:
    with open(SECRETS_PATH, "rb") as f:
        secrets = tomllib.load(f)
    s = secrets["connections"]["gsheets"]
    info = {
        "type": s["type"],
        "project_id": s["project_id"],
        "private_key_id": s["private_key_id"],
        "private_key": s["private_key"],
        "client_email": s["client_email"],
        "client_id": s["client_id"],
        "auth_uri": s["auth_uri"],
        "token_uri": s["token_uri"],
        "auth_provider_x509_cert_url": s["auth_provider_x509_cert_url"],
        "client_x509_cert_url": s["client_x509_cert_url"],
    }
    return Credentials.from_service_account_info(info, scopes=SCOPES)


def follow_redirects(url: str, timeout: int = 10) -> str:
    """단축 URL(maps.app.goo.gl 등)을 최종 URL까지 추적."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.url
    except Exception:
        return url


def resolve_url(url: str) -> str:
    if "goo.gl" in url or "maps.app" in url:
        return follow_redirects(url)
    return url


def extract_coords(url: str) -> tuple[float, float] | None:
    """
    구글 지도 URL에서 (lat, lon)을 추출.
    지원 형식: /@LAT,LON  ll=LAT,LON  query=LAT,LON  center=LAT,LON
    """
    m = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", url)
    if m:
        return float(m.group(1)), float(m.group(2))

    m = re.search(r"(?:ll|center)=(-?\d+\.\d+),(-?\d+\.\d+)", url)
    if m:
        return float(m.group(1)), float(m.group(2))

    m = re.search(r"query=(-?\d+\.\d+),(-?\d+\.\d+)", url)
    if m:
        return float(m.group(1)), float(m.group(2))

    return None


def extract_place_name(resolved_url: str) -> str | None:
    """
    리다이렉트 완료된 구글 지도 URL에서 장소명 추출.
    예: /maps/place/An+Bang+Beach/@... → "An Bang Beach"
    """
    m = re.search(r"/maps/place/([^/@?]+)", resolved_url)
    if m:
        name = urllib.parse.unquote_plus(m.group(1)).strip()
        # 숫자 좌표만 있는 경우 제외
        if re.match(r"^-?\d+\.\d+,-?\d+\.\d+$", name):
            return None
        return name if name else None
    return None


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main():
    creds   = load_creds()
    service = build("sheets", "v4", credentials=creds)
    sheet   = service.spreadsheets()

    result = sheet.values().get(
        spreadsheetId=SHEET_ID,
        range=WORKSHEET_NAME,
    ).execute()
    rows = result.get("values", [])

    if not rows:
        print("시트가 비어 있습니다.")
        return

    headers = rows[0]

    def col_idx(name: str) -> int | None:
        try:
            return headers.index(name)
        except ValueError:
            return None

    idx_maps  = col_idx(COL_MAPS)
    idx_lat   = col_idx(COL_LAT)
    idx_lon   = col_idx(COL_LON)
    idx_place = col_idx(COL_PLACE)

    if idx_maps is None or idx_lat is None or idx_lon is None:
        print(f"필수 컬럼({COL_MAPS}, {COL_LAT}, {COL_LON})을 찾을 수 없습니다.")
        return

    def cell(row: list, idx: int | None) -> str:
        if idx is None or idx >= len(row):
            return ""
        v = row[idx]
        return "" if str(v).strip() in ("", "nan") else str(v).strip()

    def col_letter(idx: int) -> str:
        result = ""
        n = idx + 1
        while n:
            n, r = divmod(n - 1, 26)
            result = chr(65 + r) + result
        return result

    updates = []

    for row_i, row in enumerate(rows[1:], start=2):
        maps_val  = cell(row, idx_maps)
        lat_val   = cell(row, idx_lat)
        lon_val   = cell(row, idx_lon)
        place_val = cell(row, idx_place)

        if not maps_val:
            continue

        needs_coords = not (lat_val and lon_val)
        needs_place  = (idx_place is not None) and (not place_val)

        if not (needs_coords or needs_place):
            continue

        print(f"행 {row_i}: {maps_val[:70]}...")
        resolved = resolve_url(maps_val)

        # 좌표 추출
        if needs_coords:
            coords = extract_coords(resolved)
            if coords:
                lat, lon = coords
                print(f"  ✅ 좌표: lat={lat}, lon={lon}")
                updates.append({"range": f"{WORKSHEET_NAME}!{col_letter(idx_lat)}{row_i}",  "values": [[lat]]})
                updates.append({"range": f"{WORKSHEET_NAME}!{col_letter(idx_lon)}{row_i}",  "values": [[lon]]})
            else:
                print(f"  ❌ 좌표 추출 실패")

        # 장소명 추출
        if needs_place:
            name = extract_place_name(resolved)
            if name:
                print(f"  ✅ 장소명: {name}")
                updates.append({"range": f"{WORKSHEET_NAME}!{col_letter(idx_place)}{row_i}", "values": [[name]]})
            else:
                print(f"  ❌ 장소명 추출 실패")

        time.sleep(0.3)

    if not updates:
        print("\n업데이트할 내용이 없습니다.")
        return

    body = {"valueInputOption": "USER_ENTERED", "data": updates}
    sheet.values().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()
    print(f"\n총 {len(updates)}개 셀 업데이트 완료.")


if __name__ == "__main__":
    main()
