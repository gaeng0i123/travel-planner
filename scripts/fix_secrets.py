import json
import os

# 1. 기본 설정 정보
PASSWORD = "admin1!"  # 원하는 비밀번호로 변경 가능
THINKLOG_DOC_ID = "1CVDWorFk3vUkEiCFV6QxTC52O8_OsErYV6yHGxS2_0Q"
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/12j2JaYTvnNmSUwJJ8zSWUuqJh5MUUe5JwftYYrz_6oY/edit?usp=sharing"

# 2. JSON 파일 읽기 (구글 서비스 계정 키)
try:
    with open('key.json', 'r') as f:
        key_data = json.load(f)
except FileNotFoundError:
    print("❌ 에러: 'key.json' 파일을 찾을 수 없습니다. 구글 서비스 계정 키 파일을 'key.json'으로 이름을 바꿔서 넣어주세요.")
    exit()

# 3. secrets.toml 내용 구성
toml_content = f"""PASSWORD = "{PASSWORD}"
THINKLOG_DOC_ID = "{THINKLOG_DOC_ID}"

[connections.gsheets]
spreadsheet = "{SPREADSHEET_URL}"
type = "{key_data.get('type')}"
project_id = "{key_data.get('project_id')}"
private_key_id = "{key_data.get('private_key_id')}"
private_key = \"\"\"{key_data.get('private_key')}\"\"\"
client_email = "{key_data.get('client_email')}"
client_id = "{key_data.get('client_id')}"
auth_uri = "{key_data.get('auth_uri')}"
token_uri = "{key_data.get('token_uri')}"
auth_provider_x509_cert_url = "{key_data.get('auth_provider_x509_cert_url')}"
client_x509_cert_url = "{key_data.get('client_x509_cert_url')}"
"""

# 4. 파일 저장 (.streamlit/secrets.toml)
os.makedirs('.streamlit', exist_ok=True)
with open('.streamlit/secrets.toml', 'w', encoding='utf-8') as f:
    f.write(toml_content)

print("✅ 성공! '.streamlit/secrets.toml' 파일이 완벽하게 생성되었습니다.")
print("이제 다른 컴퓨터에서도 'key.json'만 있으면 바로 실행 가능합니다.")
