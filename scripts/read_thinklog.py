"""
구글독스 thinklog 읽기 도구
Claude Code가 여행 대화 세션 시작 시 사전지식 확보용으로 실행

실행: python3 read_thinklog.py
"""

import tomllib
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials


def load_secrets():
    with open(".streamlit/secrets.toml", "rb") as f:
        return tomllib.load(f)


def read_thinklog():
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
        scopes=["https://www.googleapis.com/auth/documents.readonly"],
    )

    service = build("docs", "v1", credentials=creds)
    doc = service.documents().get(documentId=doc_id).execute()

    paragraphs = []
    for element in doc.get("body", {}).get("content", []):
        if "paragraph" in element:
            line = ""
            for pe in element["paragraph"]["elements"]:
                if "textRun" in pe:
                    line += pe["textRun"]["content"]
            paragraphs.append(line.rstrip("\n"))

    return "\n".join(paragraphs).strip()


if __name__ == "__main__":
    print("📖 thinklog 불러오는 중...\n")
    content = read_thinklog()
    print(content)
    print("\n✅ 읽기 완료")
