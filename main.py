import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging
import os

# 분리된 모듈에서 필요한 클래스와 함수 가져오기
from core.graph_builder import build_agent_graph
from api.chat_api import router as chat_router, set_agent_info
from api.flows_api import router as flows_router
from api.models_api import router as models_router
from api.health_api import router as health_router

from api.coding_assistant.code_api import router as coding_assistant_router
from api.vector.vector_api import router as vector_router
from api.embeddings_api import router as embeddings_router
from api.auth_api import router as auth_router
from api.tools.dynamic_tools_api import router as dynamic_tools_router
from core.database import init_database
from core.middleware import (
    AuthenticationMiddleware, RateLimitMiddleware, 
    SecurityHeadersMiddleware, RequestLoggingMiddleware
)

# 데이터베이스 초기화
print("🔄 Initializing database...")
if init_database():
    print("✅ Database initialized successfully")
else:
    print("❌ Database initialization failed")

# 그래프 구성 및 에이전트 생성
agent, tool_descriptions, agent_model_id = build_agent_graph()

# FastAPI 앱 생성 및 설정
app = FastAPI(
    title="🤖 CoE Backend API",
    description="""
    ## CoE(Center of Excellence) for AI - Backend API Server
    
    이 API는 **LangGraph 기반 AI 에이전트**와 **다양한 개발 도구**를 제공하는 백엔드 서버입니다.
    
    ### 🚀 주요 기능
    - **AI 에이전트 채팅**: OpenAI 호환 채팅 API (`/v1/chat/completions`)
    - **코딩 어시스턴트**: 코드 생성, 분석, 리팩토링, 리뷰 (`/api/coding-assistant/`)
    - **벡터 검색**: ChromaDB 기반 벡터 검색 및 RAG (`/vector/`)
    - **사용자 인증**: JWT 기반 인증 시스템 (`/auth/`)
    - **LangFlow 연동**: 워크플로우 관리 (`/flows/`)
    - **동적 도구**: 자동 도구 등록 및 관리 (`/tools/`)
    
    ### 📚 사용 가이드
    1. **인증**: `/auth/register` 또는 `/auth/login`으로 계정 생성/로그인
    2. **AI 채팅**: `/v1/chat/completions`로 AI 에이전트와 대화
    3. **코딩 지원**: `/api/coding-assistant/`로 코드 관련 작업 수행
    4. **벡터 검색**: `/vector/search`로 문서 검색
    
    ### 🔗 연동 서비스
    - **OpenWebUI**: `http://localhost:8000/v1` 설정으로 연동 가능
    - **CoE-RagPipeline**: `http://localhost:8001` (Git 분석 서비스)
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={
        "defaultModelsExpandDepth": 2,
        "defaultModelExpandDepth": 2,
        "displayRequestDuration": True,
        "docExpansion": "list",
        "filter": True,
        "showExtensions": True,
        "showCommonExtensions": True,
        "tryItOutEnabled": True
    }
)

# 미들웨어 추가 (순서 중요: 나중에 추가된 것이 먼저 실행됨)
# 1. CORS 미들웨어 (가장 먼저 실행되어야 함)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 보안 헤더 미들웨어 - 임시 비활성화
# app.add_middleware(SecurityHeadersMiddleware)

# 3. 요청 로깅 미들웨어 - uvicorn과 중복되므로 완전 비활성화
# RequestLoggingMiddleware는 uvicorn의 기본 로깅과 중복되므로 사용하지 않음
# if os.getenv("APP_ENV") == "development":
#     app.add_middleware(RequestLoggingMiddleware, log_body=True)

# 4. 속도 제한 미들웨어 - 임시 비활성화
# rate_limit = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
# app.add_middleware(RateLimitMiddleware, calls_per_minute=rate_limit)

# 5. 인증 미들웨어 (선택적 활성화) - 임시 비활성화
# enforce_auth = os.getenv("ENFORCE_AUTH", "true").lower() == "true"
# app.add_middleware(AuthenticationMiddleware, enforce_auth=enforce_auth)

# 로깅 설정 - uvicorn과 중복 방지
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True  # 기존 설정 덮어쓰기
)
logger = logging.getLogger(__name__)

# uvicorn 로거 설정 조정 (중복 로그 방지)
uvicorn_logger = logging.getLogger("uvicorn.access")
uvicorn_logger.disabled = False  # uvicorn 로그는 유지

# 루트 로거의 핸들러 중복 방지
root_logger = logging.getLogger()
if len(root_logger.handlers) > 1:
    # 중복된 핸들러 제거 (첫 번째만 유지)
    for handler in root_logger.handlers[1:]:
        root_logger.removeHandler(handler)

# 요청 로깅 미들웨어 (디버깅용) - 임시 비활성화
# @app.middleware("http")
# async def log_requests(request: Request, call_next):
#     logger.info(f"Request: {request.method} {request.url}")
#     logger.info(f"Headers: {dict(request.headers)}")
#     
#     response = await call_next(request)
#     
#     logger.info(f"Response status: {response.status_code}")
#     return response

# 에이전트 정보 설정
set_agent_info(agent, agent_model_id)

# 라우터들 등록
app.include_router(health_router)

app.include_router(auth_router)
app.include_router(models_router)
app.include_router(flows_router)
app.include_router(coding_assistant_router)
app.include_router(vector_router)
app.include_router(embeddings_router)
app.include_router(dynamic_tools_router)  # 동적 도구 API 라우터 추가
app.include_router(chat_router)

if __name__ == "__main__":
    import uvicorn

    # .env 파일 로드 (개발 환경에서만 필요)
    load_dotenv()

    # 환경 변수를 통해 개발 모드와 프로덕션 모드를 구분합니다.
    # APP_ENV가 'development'일 때만 hot-reloading을 활성화합니다.
    is_development = os.getenv("APP_ENV") == "development"

    print(f"🚀 Starting server in {'development (hot-reload enabled)' if is_development else 'production'} mode.")

    uvicorn.run(
        "main:app",
        host="0.0.0.0", port=8000, reload=is_development
    )
