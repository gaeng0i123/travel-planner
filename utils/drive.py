import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

def _get_drive_service():
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
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=creds)

def upload_to_drive(file_obj, filename: str) -> str:
    """구글 드라이브 폴더에 파일을 업로드하고 공유 링크를 반환함."""
    try:
        service = _get_drive_service()
        folder_id = st.secrets.get("DRIVE_FOLDER_ID")
        
        file_metadata = {'name': filename}
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        # 파일 포인터를 처음으로 되돌림
        file_obj.seek(0)
        media = MediaIoBaseUpload(file_obj, mimetype='image/jpeg', resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink', supportsAllDrives=True).execute()
        
        # 누구나 읽을 수 있게 권한 변경
        service.permissions().create(fileId=file.get('id'), body={'type': 'anyone', 'role': 'reader'}).execute()
        
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"드라이브 업로드 실패: {e}")
        return None
