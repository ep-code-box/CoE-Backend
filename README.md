# CoE Backend API Server

FastAPI 기반 AI 에이전트 백엔드 서버입니다.

## 🏗️ 프로젝트 구조

```
CoE-Backend/
├── api/                    # API 라우터들
├── core/                   # 핵심 로직
│   ├── app_factory.py     # 애플리케이션 팩토리
│   ├── server.py          # 서버 실행 로직
│   ├── logging_config.py  # 로깅 설정
│   └── ...
├── scripts/               # 유틸리티 스크립트
│   ├── setup_logs.sh     # 로그 디렉토리 설정
│   └── check_logs.sh     # 로그 상태 확인
├── main.py               # 애플리케이션 진입점
└── Dockerfile           # Docker 설정
```

## 🚀 실행 방법

### 로컬 개발 환경
```bash
# 의존성 설치
pip install -r requirements.txt

# 개발 모드로 실행
APP_ENV=development python main.py
```

### Docker 환경
```bash
# Docker Compose로 전체 서비스 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f coe-backend

# 컨테이너 내부에서 로그 확인
docker exec -it coe-backend /app/scripts/check_logs.sh
```

## 📝 로깅

### 로그 파일 위치
- **Docker 환경**: `/app/logs/`
- **로컬 환경**: `./logs/`

### 로그 파일 종류
- `app.log`: 애플리케이션 로그
- `access.log`: HTTP 접근 로그
- `error.log`: 에러 로그

### 로그 레벨 설정
환경 변수 `LOG_LEVEL`로 설정 가능:
- `DEBUG`: 상세한 디버그 정보
- `INFO`: 일반적인 정보 (기본값)
- `WARNING`: 경고 메시지
- `ERROR`: 에러 메시지

## 🔧 주요 변경사항

### 리팩토링 완료
1. **main.py 간소화**: 애플리케이션 생성 로직을 `core/app_factory.py`로 분리
2. **서버 실행 로직 분리**: `core/server.py`에서 서버 실행 담당
3. **로깅 시스템 개선**: Docker 환경에서 로그 파일 생성 문제 해결

### Docker 로그 설정 개선
- 로그 디렉토리 자동 생성
- 로그 파일 권한 설정
- 로그 로테이션 설정 (10MB, 5개 백업)
- UTF-8 인코딩 지원

## 🐛 문제 해결

### 로그 파일이 생성되지 않는 경우
```bash
# 컨테이너 내부에서 로그 디렉토리 확인
docker exec -it coe-backend ls -la /app/logs

# 로그 설정 스크립트 재실행
docker exec -it coe-backend /app/scripts/setup_logs.sh

# 로그 상태 확인
docker exec -it coe-backend /app/scripts/check_logs.sh
```

### 권한 문제 해결
```bash
# 호스트에서 로그 디렉토리 권한 설정
sudo chown -R 1000:1000 ./CoE-Backend/logs
chmod -R 755 ./CoE-Backend/logs
```

## 📚 API 문서

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
