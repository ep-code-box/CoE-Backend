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

# 4. 의존성 설치 (빌드 캐시 최적화)
# 소스 코드를 복사하기 전에 의존성부터 설치하여, 코드 변경 시 매번 의존성을 새로 설치하지 않도록 합니다.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 소스 코드 복사
COPY . .

# 6. 포트 노출
EXPOSE 8000

# 6. 컨테이너 실행 시 실행할 명령어
# uvicorn을 사용하여 프로덕션 환경에서 직접 FastAPI 앱 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]