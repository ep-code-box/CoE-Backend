import os
import importlib
import inspect
from typing import List, Dict, Callable, Any, Tuple
from langchain.tools import BaseTool # BaseTool 임포트

def load_all_tools() -> Tuple[Dict[str, Callable], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    'tools' 디렉토리에서 모든 도구 노드, 설명, 엣지를 동적으로 로드합니다.
    규칙:
    - 노드 함수: 이름이 '_node'로 끝나야 합니다. (예: `api_call_node`)
    - 설명 변수: 이름이 '_description' 또는 '_descriptions'로 끝나야 합니다.
    - 엣지 변수: 이름이 '_edges'로 끝나야 합니다.
    - LangChain BaseTool: BaseTool을 상속하는 클래스.
    """
    all_nodes: Dict[str, Callable] = {}
    all_tool_descriptions: List[Dict[str, Any]] = []
    all_special_edges: List[Dict[str, Any]] = []
    all_langchain_tools: List[BaseTool] = [] # LangChain BaseTool 인스턴스를 저장할 리스트

    tools_dir = os.path.dirname(__file__)
    # 현재 파일과 유틸리티 파일을 제외한 모든 파이썬 파일을 순회합니다.
    for filename in os.listdir(tools_dir):
        if filename.endswith('.py') and not filename.startswith('__') and filename not in ['utils.py', 'registry.py']:
            module_name = f"tools.{filename[:-3]}"
            module = importlib.import_module(module_name)
            
            for name, obj in inspect.getmembers(module):
                # 1. 노드 함수 수집
                if inspect.isfunction(obj) and name.endswith('_node'):
                    # 함수 이름에서 '_node'를 제거하여 노드 이름으로 사용
                    node_name = name[:-5]
                    all_nodes[node_name] = obj
                
                # 2. 도구 설명 수집
                elif name.endswith(('_description', '_descriptions')):
                    descriptions = obj if isinstance(obj, list) else [obj]
                    all_tool_descriptions.extend(descriptions)

                # 3. 엣지 정보 수집
                elif name.endswith('_edges'):
                    edges = obj if isinstance(obj, list) else [obj]
                    all_special_edges.extend(edges)
                
                # 4. LangChain BaseTool 클래스 인스턴스화 및 수집
                elif inspect.isclass(obj) and issubclass(obj, BaseTool) and obj is not BaseTool:
                    try:
                        tool_instance = obj()
                        all_langchain_tools.append(tool_instance)
                        all_tool_descriptions.append({
                            "name": tool_instance.name,
                            "description": tool_instance.description,
                            "args_schema": tool_instance.args_schema.schema() if tool_instance.args_schema else {}
                        })
                        logger.info(f"LangChain Tool loaded: {tool_instance.name}")
                    except Exception as e:
                        logger.warning(f"Failed to load LangChain Tool {name}: {e}")

    return all_nodes, all_tool_descriptions, all_special_edges
