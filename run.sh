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

# 의존성 설치/업데이트 (uv 사용)
# .installed 마커 파일이 없거나 requirements.in이 변경되었을 경우에만 설치를 진행합니다.
REQUIREMENTS_FILE="requirements.in" # uv는 requirements.in을 직접 사용
INSTALLED_MARKER="$VENV_DIR/.installed"

# requirements.in의 해시값을 저장할 파일
REQUIREMENTS_HASH_FILE="$VENV_DIR/.requirements_hash"

# 현재 requirements.in의 해시값 계산
CURRENT_HASH=$(shasum "$REQUIREMENTS_FILE" 2>/dev/null | awk '{print $1}')

# 이전 해시값 읽기
PREVIOUS_HASH=""
if [ -f "$REQUIREMENTS_HASH_FILE" ]; then
    PREVIOUS_HASH=$(cat "$REQUIREMENTS_HASH_FILE")
fi

if [ ! -f "$INSTALLED_MARKER" ] || [ "$CURRENT_HASH" != "$PREVIOUS_HASH" ]; then
    echo "📚 의존성 설치/업데이트 중 (uv 사용)..."
    pip install uv # uv 설치 또는 업데이트
    HNSWLIB_NO_NATIVE=1 uv pip install -r "$REQUIREMENTS_FILE"
    
    # 설치 완료 후 마커 파일 생성 및 해시값 저장
    touch "$INSTALLED_MARKER"
    echo "$CURRENT_HASH" > "$REQUIREMENTS_HASH_FILE"
    echo "✅ 의존성 설치/업데이트 완료"
elif [ -f "$INSTALLED_MARKER" ]; then
    echo "✅ 의존성 이미 설치됨 (requirements.in 변경 없음)"
fi

# 데이터베이스 연결 대기 함수
wait_for_db() {
    echo "⏳ 데이터베이스 연결 대기 중..."
    # .env 파일에서 DB_HOST, DB_PORT를 읽어옴
    DB_HOST=$(grep ^DB_HOST "$ENV_FILE" | cut -d '=' -f2)
    DB_PORT=$(grep ^DB_PORT "$ENV_FILE" | cut -d '=' -f2)
    
    # 기본값 설정 (grep 실패 시)
    DB_HOST=${DB_HOST:-mariadb}
    DB_PORT=${DB_PORT:-3306}

    # nc (netcat)을 사용하여 포트가 열릴 때까지 대기
    # Docker 환경에서는 host.docker.internal 대신 서비스 이름을 사용해야 할 수 있습니다.
    # 여기서는 docker-compose.yml에 정의된 mariadb 서비스 이름을 사용합니다.
    until nc -z "$DB_HOST" "$DB_PORT"; do
        echo "데이터베이스 ($DB_HOST:$DB_PORT)에 연결할 수 없습니다. 5초 후 재시도..."
        sleep 5
    done
    echo "✅ 데이터베이스 연결 성공!"
}

# 데이터베이스 연결 대기
wait_for_db

# Alembic 마이그레이션 적용 (환경변수로 비활성화 가능)
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "⬆️ Alembic 마이그레이션 적용 중..."
    alembic upgrade head
    echo "✅ Alembic 마이그레이션 완료!"
else
    echo "⏭️  Alembic 마이그레이션 건너뜀 (RUN_MIGRATIONS=false)"
fi

# .env 파일 로드 및 서버 실행
echo "🌍 환경변수 로드: .env"
echo "🎯 서버 실행 중... (http://localhost:8000)"
echo "⏹️  서버 중지: Ctrl+C"
echo ""

# 환경변수 파일을 지정하여 Python 실행
export $(grep -v '^#' "$ENV_FILE" | xargs)
python main.py
