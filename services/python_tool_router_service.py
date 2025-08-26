"""
Python 도구들을 위한 동적 API 라우터를 생성하는 서비스입니다.
"""
import os
import importlib.util
import json
from typing import Dict, Any, Callable
from fastapi import FastAPI, APIRouter

from core.schemas import AgentState

class PythonToolRouterService:
    def __init__(self, app: FastAPI):
        self.app = app
        self.tools_base_dir = "tools"

    def add_all_python_tool_routes(self):
        """
        `tools` 디렉토리를 스캔하여 `_map.py`에 정의된 모든 Python 도구의 API 엔드포인트를 동적으로 추가합니다.
        이 함수는 서버 시작 시 한번만 호출되어야 합니다.
        """
        tools_dir = os.path.abspath(self.tools_base_dir)
        print(f"\n🤖 Scanning for Python tools in: {tools_dir}")

        for root, _, files in os.walk(tools_dir):
            for filename in files:
                if filename.endswith("_map.py"):
                    self._process_map_file(root, filename)
        
        print("\n✅ Finished adding all dynamic Python tool routes.")

    def _process_map_file(self, root: str, filename: str):
        map_filepath = os.path.join(root, filename)
        tool_filepath = map_filepath.replace("_map.py", "_tool.py")

        if not os.path.exists(tool_filepath):
            return

        try:
            # 1. map 모듈에서 endpoints 정보 로드
            map_spec = importlib.util.spec_from_file_location("map_module", map_filepath)
            map_module = importlib.util.module_from_spec(map_spec)
            map_spec.loader.exec_module(map_module)
            endpoints = getattr(map_module, 'endpoints', {})

            if not endpoints:
                return

            # 2. tool 모듈 로드
            tool_spec = importlib.util.spec_from_file_location("tool_module", tool_filepath)
            tool_module = importlib.util.module_from_spec(tool_spec)
            tool_spec.loader.exec_module(tool_module)
            
            # 3. 각 엔드포인트에 대한 라우트 생성
            for tool_name, endpoint_path in endpoints.items():
                self._add_single_route(tool_name, endpoint_path, tool_module)

        except Exception as e:
            print(f"Error processing tool map {map_filepath}: {e}")

    def _add_single_route(self, tool_name: str, endpoint_path: str, tool_module: Any):
        """Helper function to create and add a single API route."""
        tool_functions = getattr(tool_module, 'tool_functions', {})
        function_to_call = tool_functions.get(tool_name)

        if not function_to_call or not callable(function_to_call):
            print(f"⚠️  Skipping route for tool '{tool_name}' ({endpoint_path}): Corresponding function not found or not callable in {tool_module.__file__}.")
            return

        router = APIRouter()
        
        # 각 엔드포인트에 대한 핸들러 함수를 동적으로 생성
        # 클로저를 사용하여 각 핸들러가 올바른 function_to_call을 참조하도록 함
        def create_handler(func: Callable) -> Callable:
            async def handler(tool_input: Dict[str, Any] = None):
                input_data = tool_input or {}
                state = AgentState(
                    history=[],
                    input=json.dumps(input_data),
                    context="direct_call"
                )
                return await func(input_data, state)
            return handler

        # FastAPI 앱에 라우트 추가
        router.add_api_route(
            endpoint_path,
            create_handler(function_to_call),
            methods=["POST"],
            tags=["Direct Tool Endpoints"],
            summary=f"Directly execute the tool '{tool_name}'"
        )
        self.app.include_router(router)
        print(f"  -> Added route: POST {endpoint_path} (for tool: {tool_name})")

# 사용 예시 (main.py에서 실행되어야 함)
# from fastapi import FastAPI
# from services.python_tool_router_service import PythonToolRouterService
# 
# app = FastAPI()
# 
# @app.on_event("startup")
# def startup_event():
#     python_tool_router = PythonToolRouterService(app)
#     python_tool_router.add_all_python_tool_routes()