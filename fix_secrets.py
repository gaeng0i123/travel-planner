import json
import os

# 1. JSON 파일 읽기
try:
    with open('key.json', 'r') as f:
        key_data = json.load(f)
except FileNotFoundError:
    print("❌ 에러: 'key.json' 파일을 찾을 수 없습니다. 이름을 확인해 주세요.")
    exit()

# 2. secrets.toml 내용 구성
# 기존 URL 유지
spreadsheet_url = "https://docs.google.com/spreadsheets/d/12j2JaYTvnNmSUwJJ8zSWUuqJh5MUUe5JwftYYrz_6oY/edit?usp=sharing"

toml_content = f"""[connections.gsheets]
spreadsheet = "{spreadsheet_url}"
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

# 3. 파일 저장
os.makedirs('.streamlit', exist_ok=True)
with open('.streamlit/secrets.toml', 'w', encoding='utf-8') as f:
    f.write(toml_content)

print("✅ 성공! '.streamlit/secrets.toml' 파일이 완벽하게 생성되었습니다.")
print("이제 '~/myproject/start.sh'를 다시 실행해 보세요.")
