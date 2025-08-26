import json
from typing import Dict, Any, List, Optional
from core.schemas import AgentState

# 1. 'run' 함수 (필수): 도구의 실제 로직
async def run(tool_input: Optional[Dict[str, Any]], state: AgentState) -> str:
    """
    현재 대화 기록을 분석하여 LangFlow 그래프 JSON 형식으로 변환합니다.
    """
    history = state.get("history", [])
    if not history:
        return json.dumps({"error": "대화 기록이 없습니다."})

    nodes = []
    edges = []
    x_pos, y_pos = 100, 100

    # 시작 노드 추가
    start_node = {
        "id": "start_node",
        "data": {"node": {"template": {"_type": "PromptNode", "content": "대화 시작"}}},
        "position": {"x": x_pos, "y": y_pos},
        "type": "PromptNode"
    }
    nodes.append(start_node)
    y_pos += 150
    
    prev_node_id = "start_node"

    # 대화 기록을 순회하며 노드와 엣지 생성
    for i, message in enumerate(history):
        role = message.get("role", "unknown")
        content = message.get("content", "")
        
        # 간단하게 내용의 첫 30자만 노드에 표시
        node_label = f"{role.upper()}: {content[:30]}..." if content else f"{role.upper()}"
        
        node_id = f"msg_node_{i}"
        node = {
            "id": node_id,
            "data": {"node": {"template": {"_type": "PromptNode", "content": node_label}}},
            "position": {"x": x_pos, "y": y_pos},
            "type": "PromptNode"
        }
        nodes.append(node)
        y_pos += 150

        # 이전 노드와 현재 노드를 연결하는 엣지 생성
        edge_id = f"edge_{i}"
        edge = {
            "id": edge_id,
            "source": prev_node_id,
            "target": node_id,
            "data": {}
        }
        edges.append(edge)
        
        prev_node_id = node_id

    # LangFlow JSON 구조 생성
    langflow_json = {
        "data": {
            "nodes": nodes,
            "edges": edges
        }
    }

    # JSON 문자열로 반환
    return json.dumps(langflow_json, indent=2, ensure_ascii=False)

# 2. 'available_tools' 변수 (필수): 도구의 명세 (Schema)
visualize_tool_schema = {
    "type": "function",
    "function": {
        "name": "visualize_conversation_as_langflow",
        "description": "지금까지의 대화 기록과 맥락을 분석하여, 전체 흐름을 시각적인 LangFlow 그래프 JSON으로 변환합니다. 사용자가 대화 내용을 '그려줘' 또는 '시각화'해달라고 요청할 때 사용합니다.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

available_tools: List[Dict[str, Any]] = [visualize_tool_schema]

# 도구 이름과 실제 함수를 매핑합니다.
tool_functions: Dict[str, callable] = {
    "visualize_conversation_as_langflow": run
}

