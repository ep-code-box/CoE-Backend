# CoE Backend - AI Agent Server

## 1. 프로젝트 개요

이 프로젝트는 **중앙 AI 에이전트 백엔드 서버**입니다. FastAPI를 기반으로 구축되었으며, 시스템의 두뇌 역할을 수행합니다.

사용자의 요청을 받아 자연어의 의도를 파악하고, 가장 적합한 **도구(Tool)**를 선택하여 실행합니다. 또한, `CoE_RagPipeline`과 같은 다른 백엔드 서비스와의 통신을 조율하여 최종 응답을 생성하는 중앙 관제탑(Orchestrator)입니다.

## 2. 주요 기능

- **중앙 에이전트 로직**: LangGraph를 활용하여 사용자의 복잡한 요청을 처리하는 핵심 에이전트 로직을 포함합니다.
- **확장 가능한 도구 시스템**: 새로운 기능을 모듈화된 '도구'로 쉽게 추가하고 확장할 수 있는 아키텍처를 제공합니다. 상세한 가이드는 [tools/README.md](./tools/README.md)를 참고하세요.
- **OpenAI 호환 API**: `/v1/chat/completions`, `/v1/embeddings` 등 표준 OpenAI 형식의 API를 제공하여 다양한 클라이언트와의 호환성을 보장합니다.
- **서비스 오케스트레이션**: RAG 파이프라인, 데이터베이스 등 외부 서비스와의 통신을 관리하고 조율합니다.

## 3. 시작하기

### 사전 요구사항

- Docker
- Docker Compose

### 실행 방법

이 서비스는 단독으로 실행되지 않으며, 프로젝트 최상위 디렉토리의 `docker-compose.yml`을 통해 전체 시스템의 일부로 실행되어야 합니다.

1.  **프로젝트 클론**:
    ```bash
    git clone <repository_url>
    cd CoE
    ```

2.  **환경 변수 설정**:
    `CoE-Backend/.env` 파일에 필요한 API 키 등의 환경 변수를 설정합니다.

3.  **Docker Compose 실행**:
    프로젝트 최상위 디렉토리에서 아래 명령어를 실행합니다.
    ```bash
    docker-compose up --build -d
    ```

4.  **로그 확인**:
    ```bash
    docker-compose logs -f coe-backend
    ```

## 4. API 사용 예시

### 에이전트와 대화하기 (`/v1/chat/completions`)

`curl`을 사용하여 에이전트에게 직접 작업을 요청할 수 있습니다. `context` 필드를 통해 현재 사용 중인 클라이언트 환경을 알려주면, 에이전트가 해당 환경에 맞는 도구들을 활성화합니다.

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d {
    "model": "ax4",
    "messages": [
      {
        "role": "user",
        "content": "1995년 3월 15일생은 만 나이로 몇 살이야?"
      }
    ],
    "context": "aider"
  }
```

## 5. 프로젝트 구조

```
CoE-Backend/
├── api/              # API 라우터 (채팅, 임베딩, 도구 등)
├── core/             # FastAPI 앱 팩토리, 서버 로직, 에이전트 노드 등 핵심 로직
├── services/         # 도구 디스패처, DB 서비스 등 비즈니스 로직
├── tools/            # 개별 도구 정의 (`_tool.py`, `_map.py`)
├── main.py           # 애플리케이션 진입점
└── Dockerfile        # Docker 설정
```

## 6. API 문서

서버 실행 후 다음 URL에서 상세한 API 문서를 확인할 수 있습니다:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## 7. 운영 시 DB 마이그레이션

- 기본값: 스킵. 컨테이너/로컬 실행 시 Alembic이 자동 실행되지 않도록 구성되어 있습니다.
- 배포 시 1회 적용:
  - Compose 환경변수: `RUN_MIGRATIONS=true docker compose up -d coe-backend`
  - 로컬 스크립트: `RUN_MIGRATIONS=true ./run.sh`
- 상세 가이드: 최상위 `docs/OPERATIONS.md`
