# 🤖 CoE-Backend: AI 에이전트 및 API 서버

**CoE(Center of Excellence) for AI** 플랫폼의 핵심 백엔드 서버입니다. **LangGraph**와 **FastAPI**를 기반으로 구축된 확장 가능한 AI 에이전트 시스템으로, 다양한 AI 워크플로우를 지원합니다.

## 🎯 핵심 가치

- **🔧 확장성**: 도구 레지스트리 패턴으로 새로운 기능을 쉽게 추가
- **🔗 호환성**: OpenWebUI, LangFlow와 완벽 호환
- **🚀 성능**: 비동기 FastAPI 기반 고성능 API 서버
- **🛡️ 안정성**: 완전한 모듈화와 체계적인 에러 처리

## ✨ 주요 기능

### 🤖 AI 에이전트 시스템
- **동적 도구 라우팅**: LLM이 사용자 요청에 최적화된 도구를 자동 선택
- **자동 도구 등록**: `tools` 디렉터리에 파일 추가만으로 새 기능 통합
- **멀티턴 대화**: 컨텍스트를 유지하는 지능형 대화 시스템

### 🔗 플랫폼 호환성
- **OpenWebUI 완벽 호환**: 표준 OpenAI API 규격 지원
- **LangFlow 연동**: 워크플로우 저장 및 관리 API 제공
- **다중 LLM 지원**: OpenAI, Anthropic 등 주요 LLM 제공업체 지원

### 🔍 검색 및 임베딩
- **벡터 검색**: ChromaDB 기반 고성능 유사도 검색
- **한국어 특화**: 한국어 최적화 임베딩 모델 지원
- **RAG 시스템**: 검색 증강 생성으로 정확한 답변 제공

### 👨‍💻 코딩 어시스턴트
- **10개 언어 지원**: Python, JavaScript, Java 등 주요 언어
- **코드 분석**: 복잡도, 품질 메트릭 자동 분석
- **자동 생성**: 코드, 테스트, 문서 자동 생성

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

## 🚀 빠른 시작

### 📋 사전 요구사항
- Python 3.8+ 또는 Docker
- OpenAI API 키 (또는 다른 LLM 제공업체 API 키)

### ⚡ 1분 설치 (Docker 권장)

```bash
# 1. 저장소 클론
git clone <repository-url>
cd CoE-Backend

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일에서 API 키 설정

# 3. Docker로 실행
docker build -t coe-backend .
docker run -d -p 8000:8000 --name coe-backend --env-file .env coe-backend

# 4. 서비스 확인
curl http://localhost:8000/health
```

### 🐍 로컬 개발 환경

```bash
# 가상 환경 설정
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 개발 서버 실행 (Hot-reload)
python main.py
```

### 🔧 환경 변수 설정

CoE-Backend는 **통합 .env 파일**로 local과 docker 환경을 모두 지원합니다.

#### 📋 환경 설정 파일

```bash
# 환경 설정 파일 생성
cp .env.example .env
# 또는 로컬 개발용
cp .env.example .env.local
```

#### 🔑 필수 설정 항목

```bash
# SKAX API 설정 (메인 LLM용)
SKAX_API_KEY=your_skax_api_key_here

# OpenAI API 설정 (임베딩용)
OPENAI_API_KEY=your_openai_api_key_here
```

#### 📊 환경별 설정 차이

| 설정 항목 | 로컬 환경 (.env.local) | Docker 환경 (오버라이드) |
|-----------|----------------------|-------------------------|
| **데이터베이스** |
| DB_HOST | localhost | mariadb |
| DB_PORT | 6667 | 3306 |
| **ChromaDB** |
| CHROMA_HOST | localhost | chroma |
| CHROMA_PORT | 6666 | 8000 |
| **Redis** |
| REDIS_HOST | localhost | redis |
| REDIS_PORT | 6669 | 6379 |

#### 🔧 완전한 .env 파일 예시

```bash
# ===================================================================
# CoE-Backend 통합 환경 설정 파일
# ===================================================================

# === API 키 설정 ===
SKAX_API_BASE=https://guest-api.sktax.chat/v1
SKAX_API_KEY=[YOUR_SKAX_API_KEY]
SKAX_MODEL_NAME=ax4

OPENAI_API_KEY=[YOUR_OPENAI_API_KEY]
OPENAI_EMBEDDING_MODEL_NAME=text-embedding-3-large

# === 데이터베이스 설정 ===
# 로컬: localhost:6667, Docker: mariadb:3306
DB_HOST=localhost
DB_PORT=6667
DB_USER=coe_user
DB_PASSWORD=coe_password
DB_NAME=coe_db

# === ChromaDB 설정 ===
# 로컬: localhost:6666, Docker: chroma:8000
CHROMA_HOST=localhost
CHROMA_PORT=6666
CHROMA_COLLECTION_NAME=coe_documents

# === Redis 설정 ===
# 로컬: localhost:6669, Docker: redis:6379
REDIS_HOST=localhost
REDIS_PORT=6669
REDIS_PASSWORD=coe_redis_password
REDIS_AUTH_DB=1

# === JWT 인증 설정 ===
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# === 애플리케이션 설정 ===
APP_ENV=development
DEBUG=true
LOG_LEVEL=DEBUG
RELOAD=true
```

#### 🚀 로컬 개발 환경 설정

##### run.sh 스크립트 활용 (권장)

```bash
# 1. 인프라 서비스만 Docker로 실행
docker-compose -f ../docker-compose.local.yml up -d

# 2. run.sh 스크립트로 실행 (.venv 자동 관리)
./run.sh
```

`run.sh` 스크립트는 다음을 자동으로 수행합니다:
- `.venv` 가상환경 자동 생성/활성화
- `requirements.txt` 의존성 자동 설치
- `.env.local` 환경변수 자동 로드
- `python main.py` 서버 실행

##### 수동 실행 방식

```bash
# 가상 환경 설정
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env.local
# .env.local 파일에서 API 키 설정

# 개발 서버 실행 (Hot-reload)
python main.py
```

## 🔌 플랫폼 연동

### 🌐 OpenWebUI 연동

OpenWebUI에서 CoE-Backend를 AI 모델로 사용할 수 있습니다.

**설정 방법:**
1. OpenWebUI **설정** → **연결** 메뉴로 이동
2. **API Base URL**: `http://localhost:8000/v1` 입력
3. **API Key**: 비워두고 저장
4. 모델 선택에서 **CoE Agent v1** 선택

**Docker 환경에서:**
```bash
# OpenWebUI와 함께 실행
docker network create coe-network
docker run --network coe-network --name coe-backend coe-backend
# OpenWebUI에서 http://coe-backend:8000/v1 사용
```

### 🔄 LangFlow 연동

LangFlow 워크플로우를 저장하고 관리할 수 있습니다.

**워크플로우 저장:**
```bash
curl -X POST http://localhost:8000/flows/save \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_workflow",
    "description": "사용자 정의 워크플로우",
    "flow_data": {...}
  }'
```

**워크플로우 조회:**
```bash
# 전체 목록
curl http://localhost:8000/flows/list

# 특정 워크플로우
curl http://localhost:8000/flows/my_workflow
```

## 💬 API 사용 예시

### 🤖 AI 에이전트 채팅

```bash
# 기본 채팅
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "coe-agent-v1",
    "messages": [{"role": "user", "content": "Python으로 웹 크롤러를 만들어줘"}]
  }'

# 스트리밍 응답
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "coe-agent-v1",
    "messages": [{"role": "user", "content": "FastAPI 서버 구조를 설명해줘"}],
    "stream": true
  }'
```

### 👨‍💻 코딩 어시스턴트

```bash
# 지원 언어 확인
curl http://localhost:8000/api/coding-assistant/languages

# 코드 분석
curl -X POST http://localhost:8000/api/coding-assistant/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "language": "python",
    "code": "def fibonacci(n):\n    if n <= 1: return n\n    return fibonacci(n-1) + fibonacci(n-2)"
  }'

# 코드 생성
curl -X POST http://localhost:8000/api/coding-assistant/generate \
  -H "Content-Type: application/json" \
  -d '{
    "language": "python",
    "description": "JWT 토큰 검증 미들웨어"
  }'
```

### 🔍 벡터 검색

```bash
# 문서 추가
curl -X POST http://localhost:8000/vector/add \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [{
      "content": "FastAPI는 Python 웹 프레임워크입니다.",
      "metadata": {"category": "framework", "language": "python"}
    }]
  }'

# 유사도 검색
curl -X POST http://localhost:8000/vector/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Python 웹 개발",
    "k": 3
  }'
```

### 📊 시스템 상태 확인

```bash
# 헬스체크
curl http://localhost:8000/health

# 사용 가능한 모델 목록
curl http://localhost:8000/v1/models

# 벡터 DB 정보
curl http://localhost:8000/vector/info
```

## 🛠️ 개발자 가이드

### 새로운 도구 추가하기

도구 레지스트리 패턴으로 `main.py` 수정 없이 새 기능을 추가할 수 있습니다.

**1단계: 도구 파일 생성**
```python
# tools/my_custom_tool.py
from typing import Dict, Any
from core.schemas import ChatState

# 도구 설명 (변수명은 _description으로 끝나야 함)
my_custom_tool_description = {
    "name": "my_custom_tool",
    "description": "사용자 정의 도구입니다."
}

# 노드 함수 (함수명은 _node로 끝나야 함)
def my_custom_tool_node(state: ChatState) -> Dict[str, Any]:
    user_message = state["messages"][-1]["content"]
    
    # 도구 로직 구현
    result = f"처리 결과: {user_message}"
    
    return {
        "messages": [{
            "role": "assistant", 
            "content": result
        }]
    }
```

**2단계: 서버 재시작**
```bash
# 개발 모드에서는 자동 재로드
python main.py

# Docker 환경에서는 컨테이너 재시작
docker restart coe-backend
```

### 고급 도구 개발

**복잡한 흐름 제어:**
```python
# tools/advanced_tool.py

# 특별한 그래프 흐름이 필요한 경우
advanced_tool_edges = {
    "advanced_tool": "human_feedback"  # 다음 노드 지정
}

def advanced_tool_node(state: ChatState) -> Dict[str, Any]:
    # 복잡한 로직 구현
    if needs_human_input:
        return {"next": "human_feedback"}
    else:
        return {"messages": [...]}
```

**외부 API 연동:**
```python
import httpx
from typing import Dict, Any

async def api_integration_node(state: ChatState) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        data = response.json()
    
    return {"messages": [{"role": "assistant", "content": str(data)}]}
```

### 프로젝트 구조 이해

```
tools/
├── registry.py          # 자동 도구 발견 및 등록
├── basic_tools.py       # 기본 도구들
├── api_tool.py         # REST API 호출 도구
├── langchain_tool.py   # LangChain 연동
└── your_tool.py        # 새로운 도구
```

**핵심 컴포넌트:**
- `core/graph_builder.py`: LangGraph 동적 구성
- `core/schemas.py`: 데이터 스키마 정의
- `tools/registry.py`: 도구 자동 등록 시스템

## 📚 API 레퍼런스

### 🤖 AI 에이전트 & 채팅
| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/v1/chat/completions` | POST | OpenAI 호환 채팅 API (핵심) |
| `/v1/models` | GET | 사용 가능한 모델 목록 |

**지원 모델:**
- `coe-agent-v1`: LangGraph 에이전트 (추천)
- `gpt-4o-mini`, `gpt-4o`: OpenAI 모델 프록시
- `claude-3-sonnet`: Anthropic 모델 프록시

### 🔍 벡터 검색 & 임베딩
| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/v1/embeddings` | POST | OpenAI 호환 임베딩 API |
| `/vector/search` | POST | 벡터 유사도 검색 |
| `/vector/add` | POST | 문서 추가 및 임베딩 |
| `/vector/info` | GET | 벡터 DB 상태 정보 |

**지원 임베딩 모델:**
- `ko-sentence-bert`: 한국어 특화 (768차원)
- `text-embedding-ada-002`: OpenAI 다국어 (1536차원)

### 👨‍💻 코딩 어시스턴트
| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/coding-assistant/languages` | GET | 지원 언어 목록 |
| `/api/coding-assistant/analyze` | POST | 코드 분석 & 메트릭 |
| `/api/coding-assistant/generate` | POST | AI 코드 생성 |
| `/api/coding-assistant/review` | POST | 코드 리뷰 |
| `/api/coding-assistant/refactor` | POST | 리팩토링 제안 |
| `/api/coding-assistant/test` | POST | 테스트 코드 생성 |

**지원 언어:** Python, JavaScript, Java, C++, Go, Rust, TypeScript, C#, PHP, Ruby

### 🔄 워크플로우 관리
| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/flows/save` | POST | LangFlow 워크플로우 저장 |
| `/flows/list` | GET | 저장된 워크플로우 목록 |
| `/flows/{name}` | GET | 특정 워크플로우 조회 |
| `/flows/{name}` | DELETE | 워크플로우 삭제 |

### 🔐 인증 & 사용자
| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/auth/register` | POST | 사용자 등록 |
| `/auth/login` | POST | 로그인 & 토큰 발급 |
| `/auth/refresh` | POST | 토큰 갱신 |
| `/auth/profile` | GET | 사용자 프로필 |

### 🏥 시스템 상태
| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/health` | GET | 서비스 상태 확인 |
| `/test/db` | GET | 데이터베이스 연결 테스트 |
| `/test/vector` | GET | 벡터 DB 연결 테스트 |

## 🔧 배포 및 운영

### Docker Compose 배포

전체 스택을 한 번에 배포하려면:

```yaml
# docker-compose.yml
version: '3.8'
services:
  coe-backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - CHROMA_HOST=chroma
    depends_on:
      - chroma
      - redis
    
  chroma:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - chroma_data:/chroma/chroma
    
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

volumes:
  chroma_data:
```

### 환경별 설정

**개발 환경:**
```bash
# .env.development
DEBUG=true
LOG_LEVEL=debug
CHROMA_HOST=localhost
```

**프로덕션 환경:**
```bash
# .env.production
DEBUG=false
LOG_LEVEL=info
CHROMA_HOST=chroma
REDIS_URL=redis://redis:6379
```

### 모니터링 및 로깅

**로그 설정:**
```python
# main.py에서 로깅 설정
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

**헬스체크:**
```bash
# 서비스 상태 모니터링
curl http://localhost:8000/health

# 응답 예시
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "services": {
    "database": "connected",
    "vector_db": "connected",
    "llm": "available"
  }
}
```

## 🔧 문제 해결

### 일반적인 문제

**1. API 키 오류**
```bash
# 환경 변수 확인
echo $OPENAI_API_KEY

# .env 파일 확인
cat .env | grep OPENAI_API_KEY
```

**2. 포트 충돌**
```bash
# 포트 사용 확인
lsof -i :8000

# 다른 포트로 실행
docker run -p 8001:8000 coe-backend
```

**3. 메모리 부족**
```bash
# Docker 메모리 제한 확인
docker stats coe-backend

# 메모리 제한 증가
docker run -m 4g coe-backend
```

### 성능 최적화

**벡터 검색 최적화:**
- 인덱스 크기 조정: `CHROMA_INDEX_SIZE=1000000`
- 배치 처리: `VECTOR_BATCH_SIZE=100`
- 캐싱 활성화: `VECTOR_CACHE_TTL=3600`

**LLM 응답 최적화:**
- 토큰 제한: `MAX_TOKENS=2000`
- 온도 조정: `TEMPERATURE=0.7`
- 스트리밍 활성화: `STREAM=true`

## 🧪 테스트

### 자동화된 테스트

```bash
# 전체 테스트 실행
python -m pytest tests/ -v

# 커버리지 포함 테스트
python -m pytest tests/ --cov=. --cov-report=html

# 특정 테스트만 실행
python -m pytest tests/test_chat_api.py::test_chat_completion
```

### 통합 테스트

```bash
# API 엔드포인트 테스트
python test_integration.py

# 부하 테스트 (선택사항)
pip install locust
locust -f tests/load_test.py --host=http://localhost:8000
```

---

## 📖 추가 문서

- **[아키텍처 상세 설계](./CoE-Backend%20상세%20설계.md)**: 시스템 아키텍처 및 기술적 세부사항
- **[LangFlow 연동 가이드](./README_LANGFLOW_INTEGRATION.md)**: LangFlow 워크플로우 연동 방법
- **[코딩 어시스턴트 가이드](./README_CODING_ASSISTANT.md)**: 코딩 어시스턴트 기능 상세 가이드

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.
