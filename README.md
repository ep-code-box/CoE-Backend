```markdown
# 🤖 CoE Backend API

이 문서는 CoE Backend API 서버의 설정 및 사용 방법을 안내합니다.

## 🚀 주요 기능

*   **AI 에이전트 채팅**: OpenAI 호환 채팅 API (`/v1/chat/completions`)
*   **코딩 어시스턴트**: 코드 생성, 분석, 리팩토링, 리뷰 (`/api/coding-assistant/`)
*   **벡터 검색**: ChromaDB 기반 벡터 검색 및 RAG (`/vector/`)
*   **LangFlow 연동**: 외부 LangFlow 서버를 통한 워크플로우 관리 (`/flows/`)
*   **동적 도구**: 자동 도구 등록 및 관리

## ⚙️ 환경 설정

### 📦 필수 설치

Python 3.10 이상 버전이 필요합니다.

```bash
# 가상 환경 생성 (선택 사항이지만 권장)
python3 -m venv .venv
source .venv/bin/activate # Linux/macOS
# .venv\Scripts\activate # Windows

# 의존성 설치
pip install -r requirements.txt
```

### 📄 환경 변수 (`.env`)

프로젝트 루트에 `.env` 파일을 생성하고 필요한 환경 변수를 설정합니다. `.env.sample` 파일을 참조하세요.

*   **`OPENAI_API_KEY`**: OpenAI API 키 (필수)
*   **`SKAX_API_KEY`**: SKT AX API 키 (SKT AX 모델 사용 시)
*   **`LANGFLOW_URL`**: 외부 LangFlow 서버의 URL (예: `http://localhost:7860`)
*   **`LANGFLOW_API_KEY`**: LangFlow 서버의 API 키 (LangFlow 서버에 설정된 경우)
*   **`EMBEDDING_MODEL_NAME`**: 기본 임베딩 모델 ID (예: `text-embedding-3-small` 또는 `bge-large-en-v1.5`)
*   **`CHROMA_HOST`**: ChromaDB 서버 호스트 (기본값: `localhost`)
*   **`CHROMA_PORT`**: ChromaDB 서버 포트 (기본값: `6666`)

### 📊 모델 설정 (`config/models.json`)

`config/models.json` 파일은 애플리케이션에서 사용할 수 있는 LLM 및 임베딩 모델을 정의합니다.

*   **외부 모델 (OpenAI, SKT AX 등):** `provider` 필드를 해당 서비스 이름으로 설정합니다. `api_base`는 필요에 따라 설정됩니다.
*   **로컬 모델:** `provider` 필드를 `"local"`로 설정하고, `api_base` 필드에 로컬 모델 서버의 주소(예: `http://localhost:11434/v1`)를 지정합니다. `model_type` 필드(`chat` 또는 `embedding`)를 통해 모델의 종류를 명시합니다.

    **예시:**
    ```json
    [
      {
        "model_id": "llava",
        "name": "Llava",
        "description": "Locally served chat model.",
        "provider": "local",
        "is_default": false,
        "api_base": "http://localhost:11434/v1",
        "model_type": "chat"
      },
      {
        "model_id": "bge-large-en-v1.5",
        "name": "BGE Large (Local)",
        "description": "Locally served embedding model.",
        "provider": "local",
        "is_default": false,
        "api_base": "http://localhost:11436/v1",
        "model_type": "embedding"
      }
    ]
    ```

### 🗄️ ChromaDB 설정

*   **로컬 환경 (Docker 미사용 시):**
    *   `CHROMA_HOST=localhost`, `CHROMA_PORT=6666`으로 설정하여 ChromaDB에 연결합니다.
    *   `chromadb` 파이썬 라이브러리 버전은 실행 중인 ChromaDB 서버 버전과 호환되어야 합니다. (예: `chromadb==1.0.17` 클라이언트는 `chromadb 1.0.x` 서버와 호환)
*   **Docker 환경:**
    *   `docker-compose.yml`에 의해 ChromaDB는 `chroma`라는 서비스 이름으로 Docker 네트워크 내부에서 실행됩니다.
    *   `coe-backend` 서비스는 Docker 네트워크를 통해 `chroma:8000`으로 ChromaDB에 접속합니다.
    *   ChromaDB 데이터는 호스트의 `./db/chroma` 디렉토리에 저장됩니다.

## ▶️ 애플리케이션 실행

프로젝트 루트에서 `run.sh` 스크립트를 실행하여 애플리케이션을 시작합니다. 이 스크립트는 가상 환경 설정 및 의존성 설치를 자동으로 처리합니다.

```bash
./run.sh
```

**개발 모드 (수동 실행):**
`run.sh` 스크립트가 아닌 수동으로 실행하려면 다음 명령어를 사용합니다.

```bash
# 가상 환경 활성화 (run.sh가 자동으로 처리)
# source .venv/bin/activate

# uvicorn 직접 실행
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 🔗 연동 서비스

*   **OpenWebUI**: `http://localhost:8000/v1` 설정으로 연동 가능
*   **CoE-RagPipeline**: `http://localhost:8001` (Git 소스코드 및 RDB 스키마 분석 서비스)
*   **LangFlow Server**: 별도로 실행되는 LangFlow 서버 (예: `http://localhost:7860`)

## 📚 API 문서

애플리케이션 실행 후, 다음 주소에서 API 문서를 확인할 수 있습니다.

*   **Swagger UI**: `http://localhost:8000/docs`
*   **Redoc**: `http://localhost:8000/redoc`

## 📂 프로젝트 구조

```
/Users/a08418/Documents/CoE/CoE-Backend/ # 프로젝트 루트 디렉토리
├───.dockerignore                  # Docker 이미지 빌드 시 제외할 파일/폴더 지정
├───.env.sample                    # 환경 변수 설정 예시 파일
├───.gitignore                     # Git 버전 관리에서 제외할 파일/폴더 지정
├───Dockerfile                     # Docker 이미지 빌드 설정 파일
├───main.py                        # FastAPI 애플리케이션 메인 진입점
├───MCP_Server_Scope.md            # Model Context Protocol 서버 범위 문서
├───README.md                      # 프로젝트 설명 및 사용 가이드
├───requirements.txt               # Python 의존성 패키지 목록
├───run.sh                         # 애플리케이션 실행 스크립트
├───__pycache__/                   # Python 컴파일된 바이트코드 캐시
├───.git/...                       # Git 버전 관리 관련 파일
├───.pytest_cache/...              # Pytest 테스트 캐시
├───.venv/...                      # Python 가상 환경 디렉토리
├───api/                           # API 엔드포인트 정의
│   ├───__init__.py                # Python 패키지 초기화
│   ├───chat_api.py                # 채팅 관련 API 엔드포인트
│   ├───embeddings_api.py          # 임베딩 관련 API 엔드포인트
│   ├───flows_api.py               # LangFlow 워크플로우 관련 API 엔드포인트
│   ├───health_api.py              # 헬스 체크 API 엔드포인트
│   ├───models_api.py              # 모델 목록 관련 API 엔드포인트
│   ├───__pycache__/               # Python 컴파일된 바이트코드 캐시
│   ├───coding_assistant/          # 코딩 어시스턴트 관련 API
│   │   ├───__init__.py            # Python 패키지 초기화
│   │   ├───code_api.py            # 코드 생성/분석 관련 API
│   │   └───__pycache__/           # Python 컴파일된 바이트코드 캐시
│   ├───tools/                     # 동적 도구 관련 API
│   │   ├───__init__.py            # Python 패키지 초기화
│   │   ├───dynamic_tools_api.py   # 동적 도구 관리 API
│   │   └───__pycache__/           # Python 컴파일된 바이트코드 캐시
│   └───vector/                    # 벡터 데이터베이스 관련 API
│       ├───__init__.py            # Python 패키지 초기화
│       ├───vector_api.py          # 벡터 검색/추가/삭제 API
│       └───__pycache__/           # Python 컴파일된 바이트코드 캐시
├───config/                        # 애플리케이션 설정 파일
│   ├───__init__.py                # Python 패키지 초기화
│   ├───models.json                # 사용 가능한 모델 정의 파일
│   └───__pycache__/               # Python 컴파일된 바이트코드 캐시
├───core/                          # 핵심 로직 및 유틸리티
│   ├───__init__.py                # Python 패키지 초기화
│   ├───agent_nodes.py             # LangGraph 에이전트 노드 정의
│   ├───database.py                # 데이터베이스 연결 및 ORM 모델 정의
│   ├───graph_builder.py           # LangGraph 그래프 빌더
│   ├───llm_client.py              # LLM 클라이언트 (모델 연동 관리)
│   ├───middleware.py              # FastAPI 미들웨어
│   ├───models.py                  # Pydantic 모델 및 모델 레지스트리
│   ├───schemas.py                 # Pydantic 스키마 정의
│   ├───tool_wrapper.py            # 도구 래퍼
│   └───__pycache__/               # Python 컴파일된 바이트코드 캐시
├───routers/                       # FastAPI 라우터 모음
│   ├───__init__.py                # Python 패키지 초기화
│   ├───router.py                  # 메인 라우터 (다른 라우터 포함)
│   └───__pycache__/               # Python 컴파일된 바이트코드 캐시
├───services/                      # 비즈니스 로직 서비스
│   ├───__init__.py                # Python 패키지 초기화
│   ├───analysis_service.py        # 분석 서비스
│   ├───chat_service.py            # 채팅 서비스
│   ├───db_service.py              # 데이터베이스 서비스 (CRUD)
│   ├───__pycache__/               # Python 컴파일된 바이트코드 캐시
│   ├───context/                   # 컨텍스트 관련 서비스
│   │   └───__pycache__/           # Python 컴파일된 바이트코드 캐시
│   ├───langflow/                  # LangFlow 연동 서비스
│   │   ├───__init__.py            # Python 패키지 초기화
│   │   ├───langflow_service.py    # 외부 LangFlow 서버 연동 로직
│   │   └───__pycache__/           # Python 컴파일된 바이트코드 캐시
│   └───vector/                    # 벡터 데이터베이스 관련 서비스
│       ├───__init__.py            # Python 패키지 초기화
│       ├───chroma_service.py      # ChromaDB 연동 서비스
│       ├───embedding_service.py   # 임베딩 서비스 (현재 사용 안 함)
│       └───__pycache__/           # Python 컴파일된 바이트코드 캐시
├───tools/                         # AI 에이전트가 사용할 도구 정의
│   ├───__init__.py                # Python 패키지 초기화
│   ├───api_tool.py                # API 호출 도구
│   ├───basic_tools.py             # 기본 유틸리티 도구
│   ├───class_tool.py              # 클래스 기반 도구
│   ├───continue-tools-integration.md # 도구 통합 문서
│   ├───guide_extraction_tool.py   # 가이드 추출 도구
│   ├───human_tool.py              # 인간 개입 도구
│   ├───langchain_tool.py          # LangChain 기반 도구
│   ├───langflow_tool.py           # LangFlow 실행 도구
│   ├───openai_tools.py            # OpenAI 도구
│   ├───rag_analysis_tool.py       # RAG 분석 도구
│   ├───README.md                  # 도구 모듈 README
│   ├───registry.py                # 도구 레지스트리
│   ├───sql_agent_tool.py          # SQL 에이전트 도구
│   ├───subgraph_tool.py           # 서브그래프 도구
│   ├───utils.py                   # 도구 관련 유틸리티
│   ├───__pycache__/               # Python 컴파일된 바이트코드 캐시
│   └───coding_assistant/          # 코딩 어시스턴트 도구
│       ├───__init__.py            # Python 패키지 초기화
│       ├───code_generation_tool.py # 코드 생성 도구
│       ├───code_refactoring_tool.py # 코드 리팩토링 도구
│       ├───code_review_tool.py    # 코드 리뷰 도구
│       ├───test_generation_tool.py # 테스트 생성 도구
│       └───__pycache__/           # Python 컴파일된 바이트코드 캐시
└───utils/                         # 공통 유틸리티 함수
    ├───__init__.py                # Python 패키지 초기화
    ├───streaming_utils.py         # 스트리밍 유틸리티
    ├───__pycache__/               # Python 컴파일된 바이트코드 캐시
    └───coding_assistant/
        ├───__init__.py            # Python 패키지 초기화
        ├───code_parser.py         # 코드 파싱 유틸리티
        ├───template_manager.py    # 템플릿 관리 유틸리티
        └───__pycache__/           # Python 컴파일된 바이트코드 캐시
```