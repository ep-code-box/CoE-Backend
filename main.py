import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging

# 분리된 모듈에서 필요한 클래스와 함수 가져오기
from core.graph_builder import build_agent_graph
from api.chat_api import router as chat_router, set_agent_info
from api.flows_api import router as flows_router
from api.models_api import router as models_router
from api.health_api import router as health_router
from api.test_api import router as test_router
from api.coding_assistant.code_api import router as coding_assistant_router
from api.vector.vector_api import router as vector_router
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
    title="CoE Backend API",
    description="CoE LangGraph Agent and API Server",
    version="1.0.0"
)

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 요청 로깅 미들웨어 (디버깅용)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    logger.info(f"Headers: {dict(request.headers)}")
    
    # POST 요청의 경우 본문 로깅 (디버깅용)
    if request.method == "POST":
        body = await request.body()
        logger.info(f"Body: {body}")
        logger.info(f"Body length: {len(body)}")
        
        # 요청 본문을 다시 읽을 수 있도록 설정
        import io
        from starlette.requests import Request as StarletteRequest
        
        async def receive():
            return {
                "type": "http.request", 
                "body": body,
                "more_body": False
            }
        
        # 새로운 Request 객체 생성
        new_request = StarletteRequest(request.scope, receive)
        response = await call_next(new_request)
    else:
        response = await call_next(request)
    
    logger.info(f"Response status: {response.status_code}")
    return response

# 에이전트 정보 설정
set_agent_info(agent, agent_model_id)

# 라우터들 등록
app.include_router(health_router)
app.include_router(test_router)
app.include_router(models_router)
app.include_router(flows_router)
app.include_router(coding_assistant_router)
app.include_router(vector_router)
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
