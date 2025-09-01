"""
동적 도구 API 모듈
tools 디렉토리의 도구들을 스캔하여 url_path가 있는 도구들을 자동으로 API 엔드포인트로 등록합니다.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import logging

from tools.core.loader import load_all_tools_dynamically as load_all_tools
from core.schemas import AgentState

logger = logging.getLogger(__name__)

# 요청/응답 모델 정의
class ToolExecutionRequest(BaseModel):
    """도구 실행 요청 모델"""
    input_data: Dict[str, Any] = {}
    messages: Optional[List[Dict[str, str]]] = None
    
class ToolExecutionResponse(BaseModel):
    """도구 실행 응답 모델"""
    success: bool
    result: Dict[str, Any]
    tool_name: str
    error: Optional[str] = None

class DynamicToolsAPI:
    """동적 도구 API 클래스"""
    
    def __init__(self):
        self.router = APIRouter(prefix="/tools", tags=["Dynamic Tools"])
        self.tool_nodes = {}
        self.tool_descriptions = []
        self._load_tools()
        self._register_endpoints()
    
    def _load_tools(self):
        """도구들을 로드하고 url_path가 있는 것들을 필터링"""
        try:
            all_nodes, all_tool_descriptions, _ = load_all_tools()
            self.tool_nodes = all_nodes
            
            # url_path가 있는 도구들만 필터링
            self.tool_descriptions = [
                desc for desc in all_tool_descriptions 
                if desc.get('url_path')
            ]
            
            logger.info(f"Loaded {len(self.tool_descriptions)} tools with URL paths")
            for desc in self.tool_descriptions:
                logger.info(f"  - {desc['name']}: {desc['url_path']}")
                
        except Exception as e:
            logger.error(f"Failed to load tools: {e}")
            self.tool_descriptions = []
    
    def _register_endpoints(self):
        """URL path가 있는 도구들을 API 엔드포인트로 등록"""
        
        # 도구 목록 조회 엔드포인트
        @self.router.get("/", response_model=List[Dict[str, Any]])
        async def list_tools():
            """등록된 모든 도구 목록을 반환합니다."""
            return self.tool_descriptions
        
        # 개별 도구 실행 엔드포인트들을 동적으로 등록
        for tool_desc in self.tool_descriptions:
            self._register_tool_endpoint(tool_desc)
    
    def _register_tool_endpoint(self, tool_desc: Dict[str, Any]):
        """개별 도구에 대한 API 엔드포인트를 등록"""
        tool_name = tool_desc['name']
        url_path = tool_desc['url_path']
        description = tool_desc['description']
        
        # 도구 노드 함수 찾기
        node_func = self.tool_nodes.get(tool_name)
        if not node_func:
            logger.warning(f"Node function not found for tool: {tool_name}")
            return
        
        # GET 엔드포인트 (도구 정보 조회)
        @self.router.get(
            url_path,
            response_model=Dict[str, Any],
            summary=f"Get {tool_name} info",
            description=f"Get information about {tool_name}: {description}"
        )
        async def get_tool_info():
            return {
                "name": tool_name,
                "description": description,
                "url_path": url_path,
                "methods": ["GET", "POST"],
                "usage": {
                    "GET": "도구 정보 조회",
                    "POST": "도구 실행"
                }
            }
        
        # POST 엔드포인트 (도구 실행)
        @self.router.post(
            url_path,
            response_model=ToolExecutionResponse,
            summary=f"Execute {tool_name}",
            description=f"Execute {tool_name}: {description}"
        )
        async def execute_tool(request: ToolExecutionRequest):
            try:
                # ChatState 구성
                state = AgentState()
                
                # 메시지가 제공된 경우 사용, 아니면 기본 메시지 생성
                if request.messages:
                    state["messages"] = request.messages
                else:
                    # input_data에서 텍스트 추출하여 기본 메시지 생성
                    user_input = request.input_data.get("text", "")
                    if not user_input:
                        user_input = json.dumps(request.input_data)
                    
                    state["messages"] = [{"role": "user", "content": user_input}]
                
                # 추가 데이터를 state에 추가
                for key, value in request.input_data.items():
                    if key not in state:
                        state[key] = value
                
                # 도구 실행 시작 로그
                logger.info(f"🚀 [API_TOOL_EXECUTION_START] Starting API execution of tool: '{tool_name}'")
                
                # 도구 실행
                result = node_func(state)
                
                # 도구 실행 완료 로그
                logger.info(f"✅ [API_TOOL_EXECUTION_COMPLETE] API execution of tool '{tool_name}' completed successfully")
                
                return ToolExecutionResponse(
                    success=True,
                    result=result,
                    tool_name=tool_name
                )
                
            except Exception as e:
                logger.error(f"❌ [API_TOOL_EXECUTION_ERROR] API execution of tool '{tool_name}' failed: {e}")
                return ToolExecutionResponse(
                    success=False,
                    result={},
                    tool_name=tool_name,
                    error=str(e)
                )
        
        # 함수 이름을 동적으로 설정 (FastAPI가 구분할 수 있도록)
        get_tool_info.__name__ = f"get_{tool_name}_info"
        execute_tool.__name__ = f"execute_{tool_name}"
        
        logger.info(f"Registered endpoints for {tool_name} at {url_path}")
        
        # 실제로 라우터에 엔드포인트를 추가하는 방법을 수정
        # FastAPI의 동적 라우트 등록 방식 사용
        self.router.add_api_route(
            url_path,
            get_tool_info,
            methods=["GET"],
            response_model=Dict[str, Any],
            summary=f"Get {tool_name} info",
            description=f"Get information about {tool_name}: {description}"
        )
        
        self.router.add_api_route(
            url_path,
            execute_tool,
            methods=["POST"],
            response_model=ToolExecutionResponse,
            summary=f"Execute {tool_name}",
            description=f"Execute {tool_name}: {description}"
        )

# 전역 인스턴스 생성
dynamic_tools_api = DynamicToolsAPI()
router = dynamic_tools_api.router