# 🤖 CoE-Backend: AI 에이전트 및 API 서버

이 프로젝트는 **CoE(Center of Excellence) for AI** 플랫폼의 핵심 백엔드 서버입니다. **LangGraph**와 **FastAPI**를 기반으로, `CoE-RagPipeline`의 분석 결과를 받아 LLM 추론을 통해 개발 가이드를 생성하는 AI 에이전트 역할을 수행합니다.

또한, **OpenWebUI** 및 **LangFlow**와 완벽하게 호환되는 인터페이스를 제공하여 다양한 AI 워크플로우를 손쉽게 구축하고 테스트할 수 있는 환경을 제공합니다.

## ✨ 주요 기능 (Features)

- **동적 도구 라우팅**: LLM을 사용하여 사용자의 요청에 가장 적합한 도구를 동적으로 선택합니다.
- **완벽한 모듈화 및 확장성**: 각 도구의 기능, 설명, 그래프 연결(흐름) 로직이 개별 파일로 분리되어 독립적으로 관리됩니다.
- **자동 도구 등록 (Tool Registry)**: `tools` 디렉터리에 새로운 도구 파일을 추가하는 것만으로 에이전트에 자동으로 통합됩니다.
- **OpenWebUI 호환**: 표준 OpenAI API 규격(`v1/chat/completions`)을 지원하여 OpenWebUI의 백엔드로 완벽하게 동작합니다.
- **LangFlow 연동**: LangFlow에서 설계한 워크플로우를 파일로 저장하고 관리할 수 있는 API를 제공합니다.
- **다양한 도구 통합**: REST API 호출, LCEL 체인, Human-in-the-Loop 등 복잡한 워크플로우를 지원하는 다양한 도구 예시를 포함합니다.
- **임베딩 모델 지원**: 한국어 특화 임베딩 모델을 포함한 다양한 임베딩 모델을 지원하며, 동적으로 모델을 추가/관리할 수 있습니다.
- **벡터 데이터베이스 연동**: ChromaDB를 통한 벡터 검색 및 RAG(Retrieval-Augmented Generation) 기능을 제공합니다.
- **다중 LLM 지원**: OpenAI, Anthropic 등 다양한 LLM 제공업체를 지원하며, `models.json`을 통해 쉽게 관리할 수 있습니다.
- **비동기 API 서버**: FastAPI 기반으로 높은 성능의 비동기 API 엔드포인트를 제공합니다.
- **Docker 지원**: Docker를 통해 일관되고 안정적인 배포 환경을 제공합니다.

## 🔧 아키텍처: 도구 레지스트리 패턴

이 프로젝트의 핵심은 **도구 레지스트리(Tool Registry)** 패턴을 사용하여 `main.py`의 수정 없이 새로운 기능을 쉽게 추가할 수 있다는 점입니다.

1.  **동적 로딩**: `tools/registry.py`의 `load_all_tools()` 함수는 `tools` 디렉터리 내의 모든 파이썬 파일을 스캔합니다.
2.  **규칙 기반 등록**: 각 파일에서 다음 규칙에 맞는 변수와 함수를 찾아 동적으로 로드합니다.
    - **노드 함수**: 이름이 `_node`로 끝나는 함수 (예: `api_call_node`)
    - **도구 설명**: 이름이 `_description` 또는 `_descriptions`로 끝나는 변수
    - **그래프 엣지**: 이름이 `_edges`로 끝나는 변수 (특별한 흐름이 필요할 경우)
3.  **그래프 자동 구성**: `main.py`는 레지스트리가 수집한 노드, 설명, 엣지 정보를 사용하여 LangGraph를 동적으로 구성합니다.

이 구조 덕분에 `main.py`는 어떤 도구가 존재하는지 알 필요가 없으며, 오직 "조립기"의 역할만 수행합니다.

## 📂 프로젝트 구조

```
CoE-Backend/
├── main.py                 # FastAPI 앱 및 메인 LangGraph 조립기
├── Dockerfile              # Docker 이미지 빌드 파일
├── .env.example            # 환경 변수 예시 파일
├── requirements.txt        # 프로젝트 의존성
├── README.md               # 프로젝트 문서
├── README_CODING_ASSISTANT.md # 코딩 어시스턴트 상세 가이드
├── debug_routes.py         # 디버그용 라우트
├── server.log              # 서버 로그 파일
├── test_coding_assistant.py # 코딩 어시스턴트 테스트
├── api/                    # API 엔드포인트 모듈
│   ├── __init__.py
│   ├── auth_api.py         # 인증 관련 API
│   ├── chat_api.py         # 채팅 API (OpenAI 호환)
│   ├── embeddings_api.py   # 임베딩 API
│   ├── flows_api.py        # LangFlow 워크플로우 API
│   ├── health_api.py       # 헬스체크 API
│   ├── models_api.py       # 모델 정보 API
│   ├── test_api.py         # 테스트 API
│   ├── coding_assistant/   # 코딩 어시스턴트 API
│   │   ├── __init__.py
│   │   └── code_api.py     # 코드 분석/생성 API
│   └── vector/             # 벡터 검색 API
│       ├── __init__.py
│       └── vector_api.py   # 벡터 검색 엔드포인트
├── config/                 # 설정 파일
│   ├── __init__.py
│   └── models.json         # 지원 모델 설정
├── core/                   # 핵심 비즈니스 로직
│   ├── __init__.py
│   ├── auth.py             # 인증 및 권한 관리
│   ├── database.py         # 데이터베이스 연결 및 모델
│   ├── graph_builder.py    # LangGraph 동적 구성
│   ├── llm_client.py       # LLM 클라이언트 초기화
│   ├── middleware.py       # 미들웨어 (CORS, 로깅 등)
│   ├── models.py           # 데이터 모델 관리
│   └── schemas.py          # Pydantic 스키마 정의
├── flows/                  # LangFlow 워크플로우 저장소
├── routers/                # 라우터 모듈
│   ├── __init__.py
│   └── router.py           # 메인 라우터 설정
├── services/               # 비즈니스 서비스 레이어
│   ├── __init__.py
│   ├── analysis_service.py # 분석 서비스
│   ├── db_service.py       # 데이터베이스 서비스
│   └── vector/             # 벡터 관련 서비스
│       ├── __init__.py
│       ├── chroma_service.py    # ChromaDB 서비스
│       └── embedding_service.py # 임베딩 서비스
├── tools/                  # 에이전트 도구 모듈
│   ├── __init__.py
│   ├── registry.py         # 도구 동적 로딩 레지스트리
│   ├── api_tool.py         # API 호출 도구
│   ├── basic_tools.py      # 기본 도구들
│   ├── class_tool.py       # 클래스 기반 도구
│   ├── guide_extraction_tool.py # 가이드 추출 도구
│   ├── human_tool.py       # Human-in-the-Loop 도구
│   ├── langchain_tool.py   # LangChain 연동 도구
│   ├── langflow_tool.py    # LangFlow 연동 도구
│   ├── subgraph_tool.py    # 서브그래프 도구
│   ├── utils.py            # 도구 유틸리티
│   └── coding_assistant/   # 코딩 어시스턴트 도구
│       ├── __init__.py
│       ├── code_generation_tool.py  # 코드 생성 도구
│       ├── code_refactoring_tool.py # 리팩토링 도구
│       ├── code_review_tool.py      # 코드 리뷰 도구
│       └── test_generation_tool.py  # 테스트 생성 도구
└── utils/                  # 유틸리티 함수
    ├── __init__.py
    ├── streaming_utils.py  # 스트리밍 관련 유틸리티
    └── coding_assistant/   # 코딩 어시스턴트 유틸리티
        ├── __init__.py
        ├── code_parser.py      # 코드 파싱 유틸리티
        └── template_manager.py # 템플릿 관리 유틸리티
```

## 🚀 시작하기

### 1. 환경 변수 설정

`.env.example` 파일을 복사하여 `.env` 파일을 생성하고, LLM API 키 등 필요한 정보를 입력합니다.

```bash
cp .env.example .env
# nano .env 또는 vi .env 명령어로 파일 편집
```

### 2. Docker를 사용하여 실행 (권장)

Docker를 사용하면 가장 쉽고 빠르게 서버를 실행할 수 있습니다.

```bash
# 1. Docker 이미지 빌드
docker build -t coe-backend .

# 2. Docker 컨테이너 실행
docker run -d -p 8000:8000 --name backend --env-file .env coe-backend
```

### 3. 로컬에서 직접 실행

```bash
# 1. 가상 환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 서버 실행 (Hot-reloading 지원)
python main.py
```

## 🔌 주요 연동 가이드

### OpenWebUI 연동

이 백엔드는 OpenWebUI와 완벽하게 호환됩니다.

1.  **OpenWebUI 설정** > **연결(Connections)** 로 이동합니다.
2.  **API 기본 URL(API Base URL)** 필드에 `http://localhost:8000/v1` 을 입력합니다.
    *   Docker 환경에서는 `CoE-Backend` 컨테이너의 IP나 Docker 호스트 IP(`http://host.docker.internal:8000/v1`)를 사용해야 할 수 있습니다.
3.  **API 키(API Key)** 는 비워두고 저장합니다.
4.  OpenWebUI 메인 화면의 모델 선택 메뉴에서 **`CoE Agent v1`** 을 선택하여 에이전트와 대화할 수 있습니다.

### LangFlow 연동

LangFlow에서 설계한 복잡한 워크플로우를 이 백엔드를 통해 저장하고 관리할 수 있습니다.

1.  LangFlow에서 워크플로우를 설계합니다.
2.  워크플로우를 내보내기(Export)하여 JSON 파일을 얻습니다.
3.  `POST /flows/save` API를 사용하여 해당 JSON을 서버에 저장할 수 있습니다. 저장된 플로우는 `flows/` 디렉터리에 파일로 관리됩니다.

```bash
# 예시: my_flow.json을 "My Awesome Flow"라는 이름으로 저장
curl -X POST http://localhost:8000/flows/save \
-H "Content-Type: application/json" \
-d '{
  "name": "My Awesome Flow",
  "description": "This is a sample flow.",
  "flow_data": { ... } # LangFlow에서 내보낸 JSON 데이터
}'
```

## 💬 사용 예시 및 테스트

### 🤖 AI 에이전트 채팅 테스트

```bash
# OpenAI 호환 채팅 API 테스트
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "coe-agent-v1",
    "messages": [
      {
        "role": "user",
        "content": "안녕하세요! CoE 에이전트 기능을 테스트해보고 싶습니다."
      }
    ]
  }'
```

### 👨‍💻 코딩 어시스턴트 테스트

```bash
# 지원 언어 목록 조회
curl -X GET "http://localhost:8000/api/coding-assistant/languages"

# Python 코드 분석
curl -X POST "http://localhost:8000/api/coding-assistant/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "language": "python",
    "code": "def hello_world():\n    print(\"Hello, World!\")"
  }'

# 코드 생성
curl -X POST "http://localhost:8000/api/coding-assistant/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "language": "python",
    "description": "사용자 인증을 위한 JWT 토큰 생성 함수"
  }'
```

### 🔍 벡터 검색 테스트

```bash
# 벡터 데이터베이스 정보 조회
curl -X GET "http://localhost:8000/vector/info"

# 문서 추가
curl -X POST "http://localhost:8000/vector/add" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "content": "CoE 플랫폼은 AI 기반 소프트웨어 개발 분석 도구입니다.",
        "metadata": {"source": "readme", "type": "documentation"}
      }
    ]
  }'

# 벡터 검색
curl -X POST "http://localhost:8000/vector/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "AI 기반 개발 도구",
    "k": 5
  }'
```

### 🔄 LangFlow 워크플로우 테스트

```bash
# 워크플로우 저장
curl -X POST "http://localhost:8000/flows/save" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test_workflow",
    "description": "테스트용 워크플로우",
    "flow_data": {"nodes": [], "edges": []}
  }'

# 워크플로우 목록 조회
curl -X GET "http://localhost:8000/flows/list"
```

## 🛠️ 새로운 도구 추가하기

이 아키텍처의 가장 큰 장점은 새로운 도구를 매우 쉽게 추가할 수 있다는 것입니다.

1.  `tools` 디렉터리에 `my_new_tool.py`와 같은 새 파이썬 파일을 만듭니다.
2.  파일 안에 아래와 같이 **도구 설명**과 **노드 함수**를 규칙에 맞게 정의합니다.

**예시: `tools/my_new_tool.py`**
```python
from typing import Dict, Any
from schemas import ChatState

# 1. 라우터가 사용할 도구 설명 (변수명은 _description 또는 _descriptions로 끝나야 함)
my_new_tool_description = {
    "name": "my_tool",
    "description": "이것은 새로 추가된 멋진 도구입니다."
}

# 2. 실제 작업을 수행할 노드 함수 (함수명은 _node로 끝나야 함)
def my_tool_node(state: ChatState) -> Dict[str, Any]:
    # ... 실제 도구 로직 구현 ...
    return {"messages": [{"role": "assistant", "content": "새로운 도구 실행 완료!"}]}
```

3.  **끝입니다!** `main.py`를 수정할 필요 없이 서버를 재시작하면 에이전트가 `my_tool`을 자동으로 인식하고 라우팅에 사용합니다.

### 복잡한 흐름 추가하기

도구가 실행된 후 특정 다른 노드로 연결되어야 한다면, `_edges` 변수를 정의하여 그래프 흐름을 지정할 수 있습니다. 자세한 내용은 `tools/` 디렉터리의 다른 도구 파일들을 참고하세요.

## 📚 API 엔드포인트

### 🤖 AI 에이전트 및 채팅
- **`POST /v1/chat/completions`**: (핵심) OpenAI 호환 채팅 API
  - `model: "coe-agent-v1"`: LangGraph 에이전트 실행
  - `model: "gpt-4o-mini"` 등: 직접 LLM 호출 (프록시)
  - OpenWebUI, LangFlow와 완벽 호환
- **`GET /v1/models`**: 사용 가능한 모델 목록 (4개 모델 지원)

### 🔍 벡터 검색 및 임베딩
- **`POST /v1/embeddings`**: OpenAI 호환 임베딩 API
  - 한국어 특화 모델(`ko-sentence-bert`) 지원
  - 다국어 모델(`text-embedding-ada-002`) 지원
- **`POST /vector/search`**: 벡터 유사도 검색
  - ChromaDB 기반 고성능 검색
  - 메타데이터 필터링 지원
- **`POST /vector/add`**: 벡터 문서 추가
  - 자동 임베딩 및 저장
  - 배치 처리 지원
- **`GET /vector/info`**: 벡터 데이터베이스 정보 조회

### 👨‍💻 코딩 어시스턴트 (10개 언어 지원)
- **`GET /api/coding-assistant/languages`**: 지원 언어 목록 조회
- **`POST /api/coding-assistant/analyze`**: 코드 분석 및 메트릭 제공
- **`POST /api/coding-assistant/template`**: 언어별 코드 템플릿 생성
- **`POST /api/coding-assistant/generate`**: AI 기반 코드 생성
- **`POST /api/coding-assistant/review`**: 코드 리뷰 및 개선 제안
- **`POST /api/coding-assistant/refactor`**: 코드 리팩토링 제안
- **`POST /api/coding-assistant/test`**: 테스트 코드 자동 생성
- **`POST /api/coding-assistant/document`**: 코드 문서화 자동 생성

### 🔄 LangFlow 워크플로우 관리
- **`POST /flows/save`**: 워크플로우 저장 (MariaDB)
- **`GET /flows/list`**: 저장된 워크플로우 목록
- **`GET /flows/{flow_name}`**: 특정 워크플로우 조회
- **`DELETE /flows/{flow_name}`**: 워크플로우 삭제

### 🔐 인증 및 사용자 관리
- **`POST /auth/register`**: 사용자 등록
- **`POST /auth/login`**: 로그인 및 토큰 발급
- **`POST /auth/refresh`**: 토큰 갱신
- **`POST /auth/logout`**: 로그아웃
- **`GET /auth/profile`**: 사용자 프로필 조회

### 🏥 시스템 관리
- **`GET /health`**: 서비스 상태 확인
- **`GET /test/db`**: 데이터베이스 연결 테스트
- **`GET /test/vector`**: 벡터 데이터베이스 테스트

## 🔧 고급 설정

### 임베딩 모델 설정

`models.json` 파일에서 임베딩 모델을 관리할 수 있습니다:

```json
{
  "embedding_models": [
    {
      "id": "ko-sentence-bert",
      "name": "Korean Sentence BERT",
      "provider": "local",
      "endpoint": "http://koEmbeddings:8000/embeddings",
      "dimensions": 768,
      "max_tokens": 512,
      "language": "ko"
    },
    {
      "id": "text-embedding-ada-002",
      "name": "OpenAI Ada v2",
      "provider": "openai",
      "dimensions": 1536,
      "max_tokens": 8191,
      "language": "multilingual"
    }
  ]
}
```

### 벡터 데이터베이스 설정

ChromaDB 연결 설정:

```python
# .env 파일
CHROMA_HOST=chroma
CHROMA_PORT=6666
CHROMA_COLLECTION_NAME=coe_documents

# 고급 설정
CHROMA_DISTANCE_FUNCTION=cosine  # cosine, l2, ip
CHROMA_MAX_RESULTS=10
CHROMA_SIMILARITY_THRESHOLD=0.7
```

### RAG 파이프라인 설정

```python
# RAG 설정
RAG_CHUNK_SIZE=1000
RAG_CHUNK_OVERLAP=200
RAG_TOP_K=5
RAG_RERANK_ENABLED=true
RAG_CONTEXT_WINDOW=4000
```

## 🔧 문제 해결

### 일반적인 문제들

#### 임베딩 서비스 연결 오류

**문제**: `Connection refused to embedding service`

**해결방법**:
```bash
# 임베딩 서비스 상태 확인
docker-compose logs koEmbeddings

# 네트워크 연결 테스트
docker-compose exec coe-backend curl http://koEmbeddings:6668/health

# 서비스 재시작
docker-compose restart koEmbeddings coe-backend
```

#### ChromaDB 연결 문제

**문제**: `ChromaDB connection timeout`

**해결방법**:
```bash
# ChromaDB 상태 확인
docker-compose logs chroma

# 데이터 볼륨 확인
docker volume ls | grep chroma

# ChromaDB 재시작
docker-compose restart chroma
```

#### 메모리 부족 오류

**문제**: 대용량 문서 처리 시 메모리 부족

**해결방법**:
```bash
# Docker 메모리 제한 증가 (docker-compose.yml)
services:
  coe-backend:
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
```

### 성능 최적화

#### 임베딩 성능 최적화
- 배치 크기 조정: `EMBEDDING_BATCH_SIZE=32`
- 캐싱 활성화: `EMBEDDING_CACHE_ENABLED=true`
- GPU 사용: CUDA 지원 임베딩 모델 사용

#### 벡터 검색 최적화
- 인덱스 최적화: 정기적인 인덱스 재구성
- 메타데이터 필터링: 불필요한 검색 범위 제한
- 결과 캐싱: 자주 사용되는 쿼리 결과 캐싱

## 🧪 테스트

### 단위 테스트 실행
```bash
# 전체 테스트
python -m pytest

# 특정 모듈 테스트
python -m pytest test_embedding.py
python -m pytest test_vector_db.py
python -m pytest test_rag.py
```

### API 테스트
```bash
# 임베딩 API 테스트
curl -X POST http://localhost:8000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"input": "안녕하세요", "model": "ko-sentence-bert"}'

# 벡터 검색 테스트
curl -X POST http://localhost:8000/vector/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Python 프로그래밍", "top_k": 5}'
```

---

자세한 사용법 및 프로젝트 전체 아키텍처는 상위 `CoE/README.md` 파일을 참고해 주세요.
