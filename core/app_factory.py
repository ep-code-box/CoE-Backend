import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import logging.config
from dotenv import load_dotenv
import time

from core.graph_builder import build_agent_graph, build_aider_agent_graph
from api.chat_api import set_agent_info
from api.flows_api import router as flows_router
from api.models_api import router as models_router
from api.health_api import router as health_router
from api.coding_assistant.code_api import router as coding_assistant_router
from api.embeddings_api import router as embeddings_router
from api.rag_api import router as rag_router
from core.database import init_database
from core.lifespan import lifespan
from core.logging_config import LOGGING_CONFIG
from services.pii_service import scrub_text


class AppFactory:
    """FastAPI 애플리케이션 생성 및 초기화를 담당하는 팩토리 클래스"""
    
    def __init__(self):
        self.agent = None
        self.aider_agent = None
        self.tool_descriptions = None
        self.aider_tool_descriptions = None
        self.agent_model_id = None
        self.aider_agent_model_id = None
    
    def initialize_database(self):
        """데이터베이스 초기화"""
        logging.info("🔄 Initializing database...")
        if init_database():
            logging.info("✅ Database initialized successfully")
            return True
        else:
            logging.error("❌ Database initialization failed")
            return False
    
    def build_agents(self):
        """에이전트 그래프 구성 및 생성"""
        logging.info("🤖 Building agent graphs...")
        self.agent, self.tool_descriptions, self.agent_model_id = build_agent_graph()
        self.aider_agent, self.aider_tool_descriptions, self.aider_agent_model_id = build_aider_agent_graph()
        logging.info("✅ Agent graphs built successfully")
    
    def create_app(self) -> FastAPI:
        """FastAPI 애플리케이션 생성 및 설정"""
        load_dotenv()
        logging.config.dictConfig(LOGGING_CONFIG)

        # 데이터베이스 초기화
        if not self.initialize_database():
            raise RuntimeError("Database initialization failed")
        
        # 에이전트 생성
        self.build_agents()
        
        # 환경에 따른 문서 노출 설정
        app_env = os.getenv("APP_ENV", "").lower()
        docs_flag = os.getenv("ENABLE_DOCS", "").lower()
        expose_docs = docs_flag in {"1", "true", "yes", "on"} or app_env in {"development", "local"}

        docs_url = "/docs" if expose_docs else None
        redoc_url = "/redoc" if expose_docs else None
        # 운영 기본은 비공개. 필요 시 ENABLE_DOCS 로 명시적으로 노출.
        openapi_url = "/openapi.json" if expose_docs else None
        root_path = os.getenv("ROOT_PATH", "")

        # 태그 메타데이터 정의
        tags_metadata = [
            {"name": "🤖 AI Chat", "description": "OpenAI 호환 채팅 인터페이스 및 LangGraph 에이전트 실행"},
            {"name": "🧠 RAG", "description": "RAG 파이프라인 연동 프로시 엔드포인트"},
            {"name": "💻 Coding Assistant", "description": "코드 분석, 템플릿 기반 생성 및 리뷰 도구"},
            {"name": "📂 Models", "description": "사용 가능한 AI 모델 목록 및 정보 조회"},
            {"name": "⚙️ Flows", "description": "LangFlow 워크플로우 관리 및 동적 엔드포인트"},
            {"name": "💎 Embeddings", "description": "OpenAI 호환 텍스트 임베딩 서비스"},
            {"name": "🛠️ Dynamic Tools", "description": "시스템에 등록된 동적 도구 실행 API"},
            {"name": "🏥 Health Check", "description": "서버 상태 확인 및 헬스 체크"},
        ]

        # FastAPI 앱 생성
        app = FastAPI(
            title="🤖 CoE Backend API",
            description="""
            ## CoE for AI - Backend API Server
            
            이 API는 **LangGraph 기반 AI 에이전트**와 **다양한 개발 도구**를 제공하는 백엔드 서버입니다.
            
            ### 🚀 주요 기능
            - **AI 에이전트 채팅**: OpenAI 호환 채팅 API (`/v1/chat/completions`)를 통해 LangGraph 에이전트와 대화
            - **Guide Agent**: 문서 및 지식 기반의 가이드 제공 (`context=guide` 또는 `guide_mode=true`)
            - **코딩 어시스턴트**: 코드 생성, 분석, 리팩토링, 리뷰 도구 제공
            - **LangFlow 연동**: 동적으로 등록된 워크플로우를 API 엔드포인트로 노출
            - **RAG 파이프라인**: Git 저장소 분석 및 벡터 검색 연동
            - **PII 보호**: 민감 정보(개인정보) 자동 마스킹 및 필터링
            
            ### 📚 사용 가이드
            1. **AI 채팅 시작**: `/v1/chat/completions`로 첫 대화를 시작하면, 응답으로 `session_id`가 발급됩니다.
            2. **대화 이어가기**: 다음 요청부터는 받은 `session_id`를 요청 본문에 포함시켜 보내면 맥락에 맞는 답변을 합니다.
            3. **동적 도구**: `/tools/` 하위에 등록된 다양한 자동화 도구들을 직접 호출할 수 있습니다.
            
            ### 🔗 연동 서비스
            - **OpenWebUI**: `http://localhost:8000/v1` 설정으로 연동 가능
            - **CoE-RagPipeline**: 소스코드/스키마 분석 및 임베딩 제공 서비스
            """,
            version="1.0.0",
            contact={
                "name": "CoE AI Support",
                "url": "https://github.com/your-repo/CoE",
            },
            license_info={
                "name": "Apache 2.0",
                "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
            },
            openapi_tags=tags_metadata,
            docs_url=docs_url,
            redoc_url=redoc_url,
            openapi_url=openapi_url,
            root_path=root_path,
            root_path_in_servers=True,
            lifespan=lifespan,
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
        
        # 미들웨어 추가
        self._add_middleware(app)
        
        # 라우터 등록
        self._register_routers(app)
        
        # 에이전트 정보 설정
        set_agent_info(self.agent, self.agent_model_id)
        
        return app
    
    def _add_middleware(self, app: FastAPI):
        """미들웨어 추가"""
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        class ForwardedPrefixMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                prefix = request.headers.get("x-forwarded-prefix")
                if prefix:
                    request.scope["root_path"] = prefix.rstrip("/")
                return await call_next(request)

        app.add_middleware(ForwardedPrefixMiddleware)
        
        # 요청 로깅 미들웨어 추가
        @app.middleware("http")
        async def log_requests(request: Request, call_next):
            start_time = time.time()

            # 요청 본문 로깅 (POST 요청의 경우) – 응답 상태 기반 필터링과 무관
            if request.method == "POST":
                try:
                    body = await request.body()
                    if body:
                        decoded = body.decode("utf-8", errors="replace")
                        masked_body, body_hits = scrub_text(decoded)
                        snippet = masked_body[:500]
                        suffix = "..." if len(masked_body) > 500 else ""
                        logging.info(
                            f"📝 {request.method} {request.url.path} body: {snippet}{suffix}"
                        )
                        if body_hits:
                            logging.info(
                                "[PII] path=%s masked_types=%s",
                                request.url.path,
                                ",".join(sorted({hit["type"] for hit in body_hits})),
                            )
                except Exception as e:
                    logging.warning(f"⚠️ Could not read request body: {e}")

            # 응답 처리
            response = await call_next(request)

            # 404 스캐너 노이즈 필터 (GET 404 중 일부 경로 무시)
            try:
                path = request.url.path or "/"
                is_get_404 = (request.method == "GET" and getattr(response, "status_code", 0) == 404)
                skip_prefixes = [
                    "/", "/favicon.ico", "/admin", "/login", "/cgi-bin", "/console", "/helpdesk",
                    "/owncloud", "/zabbix", "/WebInterface", "/api/session/properties", "/ssi.cgi",
                    "/jasperserver", "/partymgr", "/css/", "/js/", "/version"
                ]
                skip_suffixes = [".php", ".pl", ".ico", ".html", ".js", ".png"]
                is_scanner_like = (
                    path == "/" or
                    any(path.startswith(p) for p in skip_prefixes) or
                    any(path.endswith(s) for s in skip_suffixes)
                )

                if is_get_404 and is_scanner_like:
                    # 스캐너성 404는 로그 생략
                    return response
            except Exception:
                # 필터 판단 실패 시에는 일반 로깅으로 진행
                pass

            # 응답 시간 계산 및 일반 로깅
            process_time = time.time() - start_time
            client_host = request.client.host if request.client else "unknown"
            logging.info(
                f"🌐 {request.method} {request.url.path} - Client: {client_host}"
            )
            logging.info(
                f"✅ {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s"
            )

            return response
    
    def _register_routers(self, app: FastAPI):
        """라우터 등록"""
        app.include_router(health_router)
        app.include_router(models_router)
        app.include_router(flows_router)
        app.include_router(coding_assistant_router)
        app.include_router(embeddings_router)
        app.include_router(rag_router)
        
        # 동적 도구 API는 나중에 등록 (순서 중요)
        from api.tools.dynamic_tools_api import DynamicToolsAPI
        dynamic_tools_api_instance = DynamicToolsAPI()
        app.include_router(dynamic_tools_api_instance.router)
        
        # 채팅 API는 마지막에 등록
        from api.chat_api import router as chat_router
        app.include_router(chat_router)

def create_app() -> FastAPI:
    """애플리케이션 팩토리를 사용하여 FastAPI 앱 생성"""
    factory = AppFactory()
    return factory.create_app()
