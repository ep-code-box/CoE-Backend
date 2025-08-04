#!/bin/bash

# CoE-Backend 실행 스크립트
# .venv 가상환경을 활성화하고 .env 설정으로 서버를 실행합니다.

set -e  # 에러 발생 시 스크립트 중단

VENV_DIR="./.venv"
ENV_FILE="./.env"

echo "🚀 CoE-Backend 서버 시작 중..."


# .env 파일 존재 확인
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ .env 파일이 존재하지 않습니다."
    echo "📝 .env.example 파일을 복사하여 .env 파일을 생성하세요:"
    echo "   cp .env.example .env"
    echo "   nano .env  # 또는 원하는 에디터로 편집"
    echo ""
    echo "🔧 필수 설정 항목:"
    echo "   - SKAX_API_KEY: ax4 모델 사용을 위한 API 키"
    echo "   - OPENAI_API_KEY: OpenAI 서비스 사용을 위한 API 키"
    echo "   - JWT_SECRET_KEY: JWT 토큰 암호화를 위한 비밀키"
    exit 1
fi

# 가상환경 존재 확인 및 생성
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 가상환경이 존재하지 않습니다. 새로 생성합니다..."
    python3 -m venv "$VENV_DIR"
    echo "✅ 가상환경 생성 완료"
fi

# 가상환경 활성화
echo "🔄 가상환경 활성화 중..."
source "$VENV_DIR/bin/activate"

# 의존성 설치/업데이트
echo "📚 의존성 설치/업데이트 중..."
# macOS에서 chroma-hnswlib 컴파일 오류 방지
# export HNSWLIB_NO_NATIVE=1
pip install --upgrade pip
pip install -r requirements.txt

# .env 파일 로드 및 서버 실행
echo "🌍 환경변수 로드: .env"
echo "🎯 서버 실행 중... (http://localhost:8000)"
echo "⏹️  서버 중지: Ctrl+C"
echo ""

# 환경변수 파일을 지정하여 Python 실행
export $(grep -v '^#' "$ENV_FILE" | xargs)
python main.py