"""
Modal Context Protocol에 따라 '모드'별로 도구를 등록하고 관리합니다.
"""
from typing import List, Dict, Callable, Any, Tuple

# 다른 도구 파일에서 도구들을 가져옵니다.
from . import openai_tools
from . import basic_tools
# from . import continue_tools # Remove this import

# 도구 레지스트리
# 각 모드는 사용 가능한 도구의 스키마 리스트와 실제 함수 매핑을 가집니다.
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "coding": {
        "schemas": openai_tools.available_tools, # Now only openai_tools
        "functions": openai_tools.tool_functions # Now only openai_tools
    },
    "basic": {
        "schemas": basic_tools.available_tools,
        "functions": basic_tools.tool_functions
    }
    # 향후 다른 모드 (예: 'planning', 'chat')를 여기에 추가할 수 있습니다.
}

def get_tools_for_mode(mode: str) -> Tuple[List[Dict[str, Any]], Dict[str, Callable]]:
    """
    지정된 모드에 해당하는 도구 스키마와 함수를 반환합니다.
    만약 모드가 없으면 빈 리스트와 딕셔너리를 반환합니다.
    """
    mode_config = TOOL_REGISTRY.get(mode, {})
    return mode_config.get("schemas", []), mode_config.get("functions", {})

def get_all_tool_functions() -> Dict[str, Callable]:
    """
    모든 모드의 모든 도구 함수를 단일 딕셔너리로 결합하여 반환합니다.
    이름이 중복될 경우 나중에 로드된 함수가 덮어씁니다.
    """
    all_functions = {}
    for mode in TOOL_REGISTRY:
        all_functions.update(TOOL_REGISTRY[mode].get("functions", {}))
    return all_functions