# 1. 베이스 이미지 설정
# 가볍고 안정적인 Python 3.11-slim 버전을 사용합니다.
FROM python:3.11-slim

# 2. 작업 디렉토리 설정
# 컨테이너 내에서 애플리케이션 코드가 위치할 경로를 지정합니다.
WORKDIR /app

# 3. 환경 변수 설정
# Python이 .pyc 파일을 생성하지 않도록 하고, 버퍼링을 비활성화하여 로그가 즉시 출력되도록 합니다.
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# Rust 관련 환경변수 설정
# ENV RUSTFLAGS="--cfg reqwest_unstable"

# 4. 시스템 의존성 및 의존성 설치 (uv 사용)
# Rust 기반 패키지 빌드에 필요한 C 컴파일러(build-essential)를 설치합니다.
RUN apt-get update && apt-get install -y build-essential

# uv를 설치합니다.
RUN pip install uv

# requirements.in 파일을 복사합니다.
COPY requirements.in .

# uv를 사용하여 requirements.in 파일의 패키지를 바로 설치합니다.
# chroma-hnswlib 빌드 오류 방지를 위해 HNSWLIB_NO_NATIVE=1 환경 변수를 설정합니다.
RUN uv pip install --system --no-cache -r requirements.in

# 5. 소스 코드 복사
COPY . .

# 6. 로그 디렉토리 생성 및 권한 설정
RUN mkdir -p /app/logs && chmod 755 /app/logs

# 7. 로그 설정 스크립트 실행 권한 부여
RUN chmod +x /app/scripts/setup_logs.sh

# 8. 로그 디렉토리 권한 확인
RUN ls -la /app/logs

# 8. 포트 노출
EXPOSE 8000

# 9. 컨테이너 실행 시 실행할 명령어
# 로그 설정 후 uvicorn을 사용하여 프로덕션 환경에서 직접 FastAPI 앱 실행
CMD ["sh", "-c", "/app/scripts/setup_logs.sh && uvicorn main:app --host 0.0.0.0 --port 8000"]