#!/bin/bash

# 1. 프로젝트 폴더로 이동
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "=========================================="
echo "  🚀 베트남 여행 플래너 시작 중..."
echo "=========================================="

# 2. 가상 환경 체크 및 생성
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# 3. 가상 환경 활성화
source venv/bin/activate

# 4. 라이브러리 설치
echo "Installing libraries. Please wait..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# 5. 스트림릿 실행
echo "Opening Web Page..."
# 백그라운드에서 실행하고 브라우저를 엽니다.
streamlit run app.py --server.headless true &

# 6. 브라우저 열기 (3초 대기 후)
sleep 3
open "http://localhost:8501"

echo "✅ 완료! 브라우저를 확인하세요."
echo "=========================================="

# 프로세스가 종료되지 않게 대기
wait
