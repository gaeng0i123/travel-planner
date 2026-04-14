import os
import streamlit as st


def check_password() -> bool:
    """로컬 환경(LOCAL_DEV=1)에서는 로그인 스킵, 웹 배포 시에만 비밀번호 요구."""
    if os.environ.get("LOCAL_DEV") == "1":
        return True

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("🔒 Access Restricted")
        password = st.text_input("Please enter the access password", type="password")
        if st.button("Login"):
            if password == st.secrets["PASSWORD"]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ Incorrect password. Please try again.")
        return False

    return True
