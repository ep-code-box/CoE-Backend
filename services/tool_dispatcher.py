"""
Front-end에서 요청된 도구를 찾아 실행하고, 그 결과를 반환하는 서비스입니다.
"""
import os
import sys
import importlib.util
from typing import Dict, Any, Optional, List, Tuple, Callable
import logging
import httpx

from sqlalchemy.orm import Session
from core.database import LangflowToolMapping, LangFlow, SessionLocal

logger = logging.getLogger(__name__)

# 도구가 위치한 기본 디렉토리
TOOLS_BASE_DIR = "tools"
# LangFlow 실행을 위한 기본 URL
LANGFLOW_BASE_URL = os.getenv("LANGFLOW_BASE_URL", "http://localhost:8000")

async def dispatch_and_execute(tool_name: str, tool_input: Optional[Dict[str, Any]], state: "AgentState") -> Optional[Any]:
    """
    주어진 tool_name에 따라 적절한 도구를 찾아 실행합니다.

    Args:
        tool_name: 실행할 도구의 이름 (front_tool_name).
        tool_input: 도구에 전달될 입력 값.
        state: 현재 에이전트의 상태.

    Returns:
        도구 실행 결과. 도구를 찾지 못하면 None을 반환합니다.
    """
    logger.info(f"Attempting to dispatch tool: {tool_name}")

    # 1. Python 도구인지 확인하고 실행
    python_tool_path = find_python_tool_path(tool_name)
    if python_tool_path:
        logger.info(f"Found Python tool for '{tool_name}' at '{python_tool_path}'. Executing...")
        return await run_python_tool(python_tool_path, tool_input, state)

    # 2. LangFlow 도구인지 확인하고 실행
    langflow_tool = find_langflow_tool(tool_name)
    if langflow_tool:
        logger.info(f"Found LangFlow tool for '{tool_name}'. Executing...")
        return await run_langflow_tool(langflow_tool, tool_input, state)

    # 3. 해당하는 도구가 없으면 None 반환
    logger.warning(f"No tool found for '{tool_name}'.")
    return None

def find_python_tool_path(tool_name: str) -> Optional[str]:
    """
    _map.py 파일을 기반으로 Python 도구 파일의 경로를 찾습니다.

    Args:
        tool_name: 찾고자 하는 도구의 이름 (front_tool_name).

    Returns:
        도구 파일의 절대 경로. 없으면 None.
    """
    tools_dir = os.path.abspath(TOOLS_BASE_DIR)
    logger.debug(f"Searching for Python tool '{tool_name}' in: {tools_dir}")

    for root, _, files in os.walk(tools_dir):
        for filename in files:
            if filename.endswith("_map.py"):
                map_filepath = os.path.join(root, filename)
                try:
                    spec = importlib.util.spec_from_file_location("map_module", map_filepath)
                    map_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(map_module)
                    
                    # endpoints 딕셔너리의 key 값들을 front_tool_name으로 간주
                    endpoints = getattr(map_module, 'endpoints', {})
                    
                    if tool_name in endpoints.keys():
                        tool_filepath = map_filepath.replace("_map.py", "_tool.py")
                        if os.path.exists(tool_filepath):
                            logger.info(f"Found matching tool '{tool_name}' in '{map_filepath}' -> '{tool_filepath}'")
                            return tool_filepath
                        else:
                            logger.warning(f"Found map file for '{tool_name}' but corresponding _tool.py file not found at '{tool_filepath}'")
                except Exception as e:
                    logger.error(f"Error reading map file {map_filepath}: {e}")
    
    return None

def get_available_tools_for_context(context: str) -> Tuple[List[Dict[str, Any]], Dict[str, Callable]]:
    """
    주어진 컨텍스트(_map.py 기준)에 맞는, LLM이 사용할 수 있는 도구의 스키마와 함수를 반환합니다.
    """
    all_schemas = []
    all_functions = {}
    logger.info(f"Loading tools for context: '{context}'")

    tools_dir = os.path.abspath(TOOLS_BASE_DIR)
    for root, _, files in os.walk(tools_dir):
        for filename in files:
            if filename.endswith("_map.py"):
                map_filepath = os.path.join(root, filename)
                try:
                    map_spec = importlib.util.spec_from_file_location("map_module", map_filepath)
                    map_module = importlib.util.module_from_spec(map_spec)
                    map_spec.loader.exec_module(map_module)

                    tool_contexts = getattr(map_module, 'tool_contexts', [])

                    if context in tool_contexts:
                        tool_filepath = map_filepath.replace("_map.py", "_tool.py")
                        if os.path.exists(tool_filepath):
                            logger.info(f"Map file {map_filepath} matches context '{context}'. Loading tools from {tool_filepath}")
                            
                            tool_spec = importlib.util.spec_from_file_location("tool_module", tool_filepath)
                            tool_module = importlib.util.module_from_spec(tool_spec)
                            tool_spec.loader.exec_module(tool_module)

                            if hasattr(tool_module, 'available_tools') and hasattr(tool_module, 'tool_functions'):
                                all_schemas.extend(getattr(tool_module, 'available_tools'))
                                all_functions.update(getattr(tool_module, 'tool_functions'))
                        else:
                            logger.warning(f"Map file {map_filepath} matched context, but tool file {tool_filepath} not found.")

                except Exception as e:
                    logger.error(f"Error processing map file {map_filepath}: {e}")

    # LangFlow 도구는 현재 컨텍스트 필터링을 지원하지 않음 (향후 추가 가능)
    logger.info(f"Found {len(all_schemas)} tools available for context '{context}'.")
    return all_schemas, all_functions

def find_langflow_tool(tool_name: str) -> Optional[LangflowToolMapping]:
    """
    데이터베이스 매핑 테이블을 기반으로 LangFlow 도구를 찾습니다.
    """
    db: Session = SessionLocal()
    try:
        return db.query(LangflowToolMapping).filter(LangflowToolMapping.front_tool_name == tool_name).first()
    except Exception as e:
        logger.error(f"Error finding LangFlow tool '{tool_name}' in database: {e}", exc_info=True)
        return None
    finally:
        db.close()

async def run_python_tool(tool_path: str, tool_input: Optional[Dict[str, Any]], state: "AgentState") -> Any:
    """
    주어진 경로의 Python 도구를 동적으로 로드하고 실행합니다.
    도구 파일에는 'run(tool_input, state)' 함수가 정의되어 있어야 합니다.
    """
    try:
        # 모듈 이름을 경로로부터 생성 (e.g., tools.coding_assistant.my_tool)
        module_name = os.path.splitext(os.path.relpath(tool_path, "."))[0].replace(os.path.sep, '.')
        
        spec = importlib.util.spec_from_file_location(module_name, tool_path)
        if spec is None:
            raise ImportError(f"Could not create module spec for {tool_path}")
            
        tool_module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = tool_module
        spec.loader.exec_module(tool_module)

        # 도구 모듈에 'run' 함수가 있는지 확인
        if hasattr(tool_module, 'run') and callable(getattr(tool_module, 'run')):
            logger.info(f"Executing run() function in {tool_path}")
            # 'run' 함수 실행. tool_input이 없으면 None을 전달하며, 이 경우 run 함수 내부에서
            # state 정보를 바탕으로 필요한 입력을 파싱해야 합니다.
            return await getattr(tool_module, 'run')(tool_input, state)
        else:
            raise AttributeError(f"Tool module at {tool_path} does not have a callable 'run' function.")

    except Exception as e:
        logger.error(f"Failed to execute Python tool at {tool_path}: {e}", exc_info=True)
        # 에러 발생 시, 사용자에게 보여줄 수 있는 형태로 에러 메시지 반환
        return {"error": f"An error occurred while running the tool: {str(e)}"}

async def run_langflow_tool(tool: LangflowToolMapping, tool_input: Optional[Dict[str, Any]], state: "AgentState") -> Any:
    """
    찾아낸 LangFlow 도구를 실행합니다.
    """
    db: Session = SessionLocal()
    try:
        # tool 매핑 정보에서 flow_id를 사용하여 LangFlow의 엔드포인트(name)를 찾습니다.
        langflow = db.query(LangFlow).filter(LangFlow.flow_id == tool.flow_id).first()
        if not langflow:
            return {"error": f"LangFlow with flow_id '{tool.flow_id}' not found in the database."}
        
        endpoint_name = langflow.name
        execution_url = f"{LANGFLOW_BASE_URL}/flows/run/{endpoint_name}"

        # TODO: tool_input이 없으면 state['history']에서 정보를 추출하는 로직 구현
        # 현재는 tool_input이 있는 경우만 가정합니다.
        if tool_input is None:
            # 이 부분은 추후 자연어 처리 등을 통해 입력값을 동적으로 생성해야 합니다.
            logger.warning("tool_input is missing for LangFlow tool. This needs to be implemented.")
            # 임시로 빈 입력을 전달하거나, 에러를 반환할 수 있습니다.
            request_body = {"user_input": ""} # 또는 다른 기본값
        else:
            request_body = {"user_input": tool_input}

        logger.info(f"Calling LangFlow execution endpoint: {execution_url}")
        async with httpx.AsyncClient() as client:
            response = await client.post(execution_url, json=request_body, timeout=60.0)
            response.raise_for_status() # 4xx, 5xx 에러 발생 시 예외 처리
            return response.json()

    except httpx.RequestError as e:
        logger.error(f"HTTP request to LangFlow failed: {e}", exc_info=True)
        return {"error": f"Failed to connect to LangFlow service: {str(e)}"}
    except httpx.HTTPStatusError as e:
        logger.error(f"LangFlow service returned an error: {e.response.status_code} {e.response.text}", exc_info=True)
        return {"error": f"LangFlow service error: {e.response.status_code}", "detail": e.response.text}
    except Exception as e:
        logger.error(f"Failed to execute LangFlow tool '{tool.front_tool_name}': {e}", exc_info=True)
        return {"error": f"An unexpected error occurred while running the LangFlow tool: {str(e)}"}
    finally:
        db.close()
