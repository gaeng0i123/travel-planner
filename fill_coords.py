"""
구글 시트 '상세일정' 탭에서 구글지도 링크만 있고 좌표(lat/lon)가 없는 행에
좌표를 자동으로 채워 넣는 스크립트.

사용법:
    python3 fill_coords.py
"""

import re
import time
import tomllib
import urllib.request
from pathlib import Path

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


# ── 설정 ──────────────────────────────────────────────────────────────────────

SECRETS_PATH = Path(".streamlit/secrets.toml")
SHEET_ID = "12j2JaYTvnNmSUwJJ8zSWUuqJh5MUUe5JwftYYrz_6oY"
WORKSHEET_NAME = "상세일정"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

# 컬럼 헤더 이름 (시트 1행 기준)
COL_MAPS = "구글지도"
COL_LAT  = "lat"
COL_LON  = "lon"


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


def extract_coords(url: str) -> tuple[float, float] | None:
    """
    구글 지도 URL에서 (lat, lon)을 추출.
    - 단축 링크는 리다이렉트 추적 후 파싱.
    지원 형식:
      /@LAT,LON,  /maps/place/.../@LAT,LON
      ll=LAT,LON  query=LAT,LON  center=LAT,LON
    """
    if not url or str(url).strip() in ("", "nan"):
        return None

    url = str(url).strip()

    # 단축 링크 → 실제 URL 추적
    if "goo.gl" in url or "maps.app" in url:
        url = follow_redirects(url)

    # 패턴 1: @lat,lon  (가장 흔한 형식)
    m = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", url)
    if m:
        return float(m.group(1)), float(m.group(2))

    # 패턴 2: ll=lat,lon  또는  center=lat,lon
    m = re.search(r"(?:ll|center)=(-?\d+\.\d+),(-?\d+\.\d+)", url)
    if m:
        return float(m.group(1)), float(m.group(2))

    # 패턴 3: query=lat,lon  (주소가 아닌 숫자 좌표인 경우)
    m = re.search(r"query=(-?\d+\.\d+),(-?\d+\.\d+)", url)
    if m:
        return float(m.group(1)), float(m.group(2))

    return None


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main():
    creds = load_creds()
    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets()

    # 시트 전체 읽기
    result = sheet.values().get(
        spreadsheetId=SHEET_ID,
        range=WORKSHEET_NAME,
    ).execute()
    rows = result.get("values", [])

    if not rows:
        print("시트가 비어 있습니다.")
        return

    headers = rows[0]
    try:
        col_maps_idx = headers.index(COL_MAPS)
        col_lat_idx  = headers.index(COL_LAT)
        col_lon_idx  = headers.index(COL_LON)
    except ValueError as e:
        print(f"헤더를 찾을 수 없습니다: {e}")
        return

    updates = []  # (row_num_1based, lat, lon)

    for row_i, row in enumerate(rows[1:], start=2):  # 2행부터 (1행=헤더)
        # 행이 짧으면 해당 컬럼이 없는 것 → 빈 값으로 간주
        maps_val = row[col_maps_idx] if col_maps_idx < len(row) else ""
        lat_val  = row[col_lat_idx]  if col_lat_idx  < len(row) else ""
        lon_val  = row[col_lon_idx]  if col_lon_idx  < len(row) else ""

        has_link = bool(maps_val and maps_val.strip())
        has_lat  = bool(lat_val  and str(lat_val).strip() not in ("", "nan"))
        has_lon  = bool(lon_val  and str(lon_val).strip() not in ("", "nan"))

        if has_link and not (has_lat and has_lon):
            print(f"  행 {row_i}: 좌표 추출 시도 → {maps_val[:60]}...")
            coords = extract_coords(maps_val)
            if coords:
                lat, lon = coords
                print(f"    ✅ lat={lat}, lon={lon}")
                updates.append((row_i, lat, lon))
            else:
                print(f"    ❌ 좌표를 찾지 못했습니다.")
            time.sleep(0.3)  # API 과부하 방지

    if not updates:
        print("업데이트할 행이 없습니다. (이미 모두 좌표가 있거나 지도 링크가 없음)")
        return

    # 배치 업데이트
    def col_letter(idx: int) -> str:
        """0-based index → A, B, C ..."""
        result = ""
        idx += 1
        while idx:
            idx, r = divmod(idx - 1, 26)
            result = chr(65 + r) + result
        return result

    lat_col  = col_letter(col_lat_idx)
    lon_col  = col_letter(col_lon_idx)

    data_list = []
    for row_num, lat, lon in updates:
        data_list.append({
            "range": f"{WORKSHEET_NAME}!{lat_col}{row_num}",
            "values": [[lat]],
        })
        data_list.append({
            "range": f"{WORKSHEET_NAME}!{lon_col}{row_num}",
            "values": [[lon]],
        })

    body = {"valueInputOption": "USER_ENTERED", "data": data_list}
    sheet.values().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()
    print(f"\n총 {len(updates)}개 행 업데이트 완료.")


if __name__ == "__main__":
    main()
