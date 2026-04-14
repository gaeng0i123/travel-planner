import streamlit as st
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials


def _read_thinklog_from_docs() -> str:
    try:
        s = st.secrets["connections"]["gsheets"]
        creds = Credentials.from_service_account_info(
            {
                "type": s["type"], "project_id": s["project_id"],
                "private_key_id": s["private_key_id"], "private_key": s["private_key"],
                "client_email": s["client_email"], "client_id": s["client_id"],
                "auth_uri": s["auth_uri"], "token_uri": s["token_uri"],
                "auth_provider_x509_cert_url": s["auth_provider_x509_cert_url"],
                "client_x509_cert_url": s["client_x509_cert_url"],
            },
            scopes=["https://www.googleapis.com/auth/documents.readonly"],
        )
        service = build("docs", "v1", credentials=creds)
        doc = service.documents().get(documentId=st.secrets["THINKLOG_DOC_ID"]).execute()
        paragraphs = []
        for element in doc.get("body", {}).get("content", []):
            if "paragraph" in element:
                line = ""
                for pe in element["paragraph"]["elements"]:
                    if "textRun" in pe:
                        line += pe["textRun"]["content"]
                paragraphs.append(line.rstrip("\n"))
        return "\n".join(paragraphs).strip()
    except Exception as e:
        return f"구글 독스 읽기 실패: {e}"


def render() -> None:
    st.header("💬 AI 여행 비서")

    if st.button("🔄 독스에서 최신 내용 불러오기"):
        st.session_state.pop("thinklog", None)
        st.rerun()

    thinklog = st.session_state.get("thinklog") or _read_thinklog_from_docs()
    st.session_state["thinklog"] = thinklog

    st.caption("📝 나의 여행 고민 로그 (구글 독스 원본)")
    with st.container(border=True):
        st.markdown("""
<style>
.thinklog{color:inherit;}
.thinklog h1{font-size:1.2rem !important;margin:8px 0 4px;color:inherit;}
.thinklog h2{font-size:1.05rem !important;margin:6px 0 3px;color:inherit;}
.thinklog h3{font-size:0.95rem !important;margin:4px 0 2px;color:inherit;}
.thinklog p{font-size:0.9rem !important;margin:2px 0;line-height:1.6;color:inherit;}
.thinklog li{font-size:0.9rem !important;line-height:1.6;color:inherit;}
</style>
""", unsafe_allow_html=True)
        st.markdown(f'<div class="thinklog">{thinklog}</div>', unsafe_allow_html=True)

    st.divider()

    st.markdown("### 🤖 AI에게 물어보기")
    st.info("Claude Code와 여행 고민을 대화한 뒤 **'정리해줘'** 라고 하면 대화 내용이 위 독스에 자동으로 기록됩니다.")
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        st.link_button("Gemini 열기", "https://gemini.google.com", use_container_width=True)
    with col_a2:
        st.link_button("Claude 열기", "https://claude.ai", use_container_width=True)
