"""
구글독스 thinklog 업데이트 도구
사용법: Claude Code가 "정리해줘" 요청 받았을 때 직접 실행

실행: python3 update_thinklog.py
→ 업데이트할 내용을 stdin으로 받거나 코드 내 content 변수에 직접 작성
"""

import sys
import tomllib
from datetime import date
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials


def load_secrets():
    with open(".streamlit/secrets.toml", "rb") as f:
        return tomllib.load(f)


def append_to_thinklog(content: str):
    secrets = load_secrets()
    s = secrets["connections"]["gsheets"]
    doc_id = secrets["THINKLOG_DOC_ID"]

    creds = Credentials.from_service_account_info(
        {
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
        },
        scopes=["https://www.googleapis.com/auth/documents"],
    )

    service = build("docs", "v1", credentials=creds)

    # 현재 문서 끝 위치 확인
    doc = service.documents().get(documentId=doc_id).execute()
    end_index = doc["body"]["content"][-1]["endIndex"] - 1

    # 날짜 헤더 + 내용 추가
    today = date.today().strftime("%Y-%m-%d")
    text_to_insert = f"\n\n---\n[{today}]\n{content.strip()}\n"

    service.documents().batchUpdate(
        documentId=doc_id,
        body={
            "requests": [
                {
                    "insertText": {
                        "location": {"index": end_index},
                        "text": text_to_insert,
                    }
                }
            ]
        },
    ).execute()

    print(f"✅ thinklog 업데이트 완료 ({today})")


if __name__ == "__main__":
    # 인자로 내용 전달 또는 stdin 사용
    if len(sys.argv) > 1:
        content = " ".join(sys.argv[1:])
    else:
        print("내용을 입력하세요 (Ctrl+D로 종료):")
        content = sys.stdin.read()

    if content.strip():
        append_to_thinklog(content)
    else:
        print("❌ 내용이 없습니다.")
