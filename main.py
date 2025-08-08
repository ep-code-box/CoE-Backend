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

from api.tools.dynamic_tools_api import router as dynamic_tools_router
from core.database import init_database


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
    ## CoE for AI - Backend API Server
    
    이 API는 **LangGraph 기반 AI 에이전트**와 **다양한 개발 도구**를 제공하는 백엔드 서버입니다.
    
    ### 🚀 주요 기능
    - **AI 에이전트 채팅**: OpenAI 호환 채팅 API (`/v1/chat/completions`)
    - **코딩 어시스턴트**: 코드 생성, 분석, 리팩토링, 리뷰 (`/api/coding-assistant/`)
    - **벡터 검색**: ChromaDB 기반 벡터 검색 및 RAG (`/vector/`)
    - **LangFlow 연동**: 워크플로우 관리 (`/flows/`)
    - **동적 도구**: 자동 도구 등록 및 관리 (`/tools/`)
    
    ### 📚 사용 가이드
    1. **AI 채팅 시작**: `/v1/chat/completions`로 첫 대화를 시작하면, 응답으로 `session_id`가 발급됩니다.
    2. **대화 이어가기**: 다음 요청부터는 받은 `session_id`를 요청 본문에 포함시켜 보내면, AI가 이전 대화 내용을 기억하고 맥락에 맞는 답변을 합니다.
    3. **코딩 지원 및 벡터 검색**: 필요에 따라 다른 API들을 활용하여 개발 작업을 보조할 수 있습니다.
    
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



# 로깅 설정: 모든 로그를 하나의 핸들러로 처리
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True  # 기존 설정 덮어쓰기
)
logger = logging.getLogger(__name__)

# tool_tracker 로거는 이제 기본 로깅 설정을 따르도록 propagate=True (기본값) 유지
# 별도의 핸들러를 추가하지 않음
tool_logger = logging.getLogger("tool_tracker")
tool_logger.setLevel(logging.INFO) # tool_tracker 로거의 레벨 설정
tool_logger.propagate = True # 루트 로거로 전파

# uvicorn 로거 설정 조정 (중복 로그 방지)
uvicorn_logger = logging.getLogger("uvicorn.access")
uvicorn_logger.disabled = False  # uvicorn 로그는 유지

# 루트 로거의 핸들러 중복 방지 (basicConfig가 이미 처리하지만, 혹시 모를 경우 대비)
root_logger = logging.getLogger()
if len(root_logger.handlers) > 1:
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
        host="0.0.0.0", port=8000, reload=is_development,
        reload_dirs=["api", "config","core", "routers", "services", "flows", "tools", "utils"],  # 감시할 디렉토리 지정
        reload_excludes=[".*", ".py[cod]", "__pycache__", ".env", ".venv", ".git", "output","gitsync"]  # 감시를 제외할 파일 지정
    )
