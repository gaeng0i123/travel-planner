#!/bin/bash

echo "🚀 베트남 여행 플래너 시동 중..."

# 1. 가상환경(venv) 체크 및 생성
if [ ! -d "venv" ]; then
    echo "📦 가상환경이 없습니다. 새로 생성합니다..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "✅ 가상환경이 확인되었습니다. 활성화합니다."
    source venv/bin/activate
fi

# 2. .streamlit/secrets.toml 체크
if [ ! -f ".streamlit/secrets.toml" ]; then
    echo "🔑 설정 파일(secrets.toml)이 없습니다."
    if [ -f "key.json" ]; then
        echo "🛠️ key.json을 발견했습니다. 설정을 자동 생성합니다..."
        python3 fix_secrets.py
    else
        echo "❌ 에러: key.json 파일이 없습니다. 구글 서비스 계정 키를 넣어주세요."
        exit 1
    fi
fi

# 3. Streamlit 서버 실행
echo "🌐 서버를 실행합니다! 브라우저 창이 열릴 때까지 잠시만 기다려 주세요..."
streamlit run app.py
