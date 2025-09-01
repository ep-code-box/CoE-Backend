"""
새로운 동적 도구 로더.
`_tool.py`와 `_map.py` 파일을 스캔하여 도구 정보를 동적으로 로드합니다.
"""
import os
import importlib.util
from typing import List, Dict, Callable, Any, Tuple
import logging

logger = logging.getLogger(__name__)
TOOLS_BASE_DIR = "tools"

def load_all_tools_dynamically() -> Tuple[Dict[str, Callable], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    `tools` 디렉토리에서 모든 도구를 동적으로 로드하여 반환합니다.
    기존 `tools.core.registry.load_all_tools`와 동일한 데이터 구조를 반환하여 호환성을 유지합니다.

    Returns:
        - all_nodes: {tool_name: node_function} 딕셔너리
        - all_tool_descriptions: 도구 설명 딕셔너리 리스트
        - all_edges: 엣지 설정 딕셔너리 리스트 (현재는 미사용)
    """
    all_nodes = {}
    all_tool_descriptions = []
    all_edges = [] # 하위 호환성을 위해 유지

    tools_dir = os.path.abspath(TOOLS_BASE_DIR)
    logger.info(f"Dynamically loading tools from: {tools_dir}")

    for root, _, files in os.walk(tools_dir):
        for filename in files:
            if filename.endswith("_tool.py"):
                tool_path = os.path.join(root, filename)
                map_path = tool_path.replace("_tool.py", "_map.py")

                try:
                    # 1. _tool.py 파일 로드
                    tool_module_name = f"tools.{os.path.splitext(filename)[0]}"
                    spec = importlib.util.spec_from_file_location(tool_module_name, tool_path)
                    tool_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(tool_module)

                    # 2. _map.py 파일 로드 (선택 사항)
                    endpoints = {}
                    if os.path.exists(map_path):
                        map_module_name = f"tools.{os.path.splitext(filename)[0]}_map"
                        map_spec = importlib.util.spec_from_file_location(map_module_name, map_path)
                        map_module = importlib.util.module_from_spec(map_spec)
                        map_spec.loader.exec_module(map_module)
                        endpoints = getattr(map_module, 'endpoints', {})

                    # 3. 도구 정보 추출 및 변환
                    tool_functions = getattr(tool_module, 'tool_functions', {})
                    available_tools_schemas = getattr(tool_module, 'available_tools', [])

                    for schema in available_tools_schemas:
                        func_name = schema.get("function", {}).get("name")
                        if func_name in tool_functions:
                            # 노드 함수 매핑
                            all_nodes[func_name] = tool_functions[func_name]
                            
                            # 도구 설명 생성
                            description = schema.get("function", {}).get("description", "")
                            url_path = endpoints.get(func_name) # _map.py에서 url_path 가져오기
                            
                            desc_entry = {
                                "name": func_name,
                                "description": description
                            }
                            if url_path:
                                desc_entry["url_path"] = url_path
                            
                            all_tool_descriptions.append(desc_entry)

                except Exception as e:
                    logger.error(f"Error loading tool from {tool_path}: {e}", exc_info=True)

    logger.info(f"Successfully loaded {len(all_nodes)} tool functions and {len(all_tool_descriptions)} descriptions.")
    return all_nodes, all_tool_descriptions, all_edges
