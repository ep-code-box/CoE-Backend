import json
from typing import Dict, Any, List, Optional
from core.schemas import AgentState
from core.llm_client import get_client_for_model # LLM 호출을 위해 추가

# 1. 'run' 함수 (필수): 대화 시각화 도구의 실제 로직
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
        
        # 'user' 또는 'assistant' 역할의 메시지만 시각화합니다.
        if role not in ["user", "assistant"]:
            continue # 다른 역할(예: 'system', 내부 LLM 판단 메시지)은 건너뜁니다.
        
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

# --- 새로운 도구: LangFlow 워크플로우 생성 도구 ---
async def generate_langflow_workflow_run(tool_input: Optional[Dict[str, Any]], state: AgentState) -> str:
    """
    사용자의 요청을 바탕으로 LangFlow 워크플로우 JSON을 생성합니다.
    """
    user_query = tool_input.get("input", "")
    model_id = state.get("model_id") # 에이전트가 사용하는 LLM 모델 사용

    if not user_query:
        return json.dumps({"error": "LangFlow 생성을 위한 요청 내용이 없습니다."})

    llm_client = get_client_for_model(model_id)

    # LLM에게 LangFlow JSON 생성을 지시하는 시스템 프롬프트
    system_prompt_content = """당신은 LangFlow 워크플로우를 설계하고 JSON으로 출력하는 전문 아키텍트입니다.
사용자의 요청을 분석하여, 해당 기능을 수행하는 LangFlow 워크플로우의 JSON 정의를 생성하세요.
생성된 JSON은 LangFlow UI에서 가져오기(Import)하여 바로 사용할 수 있는 유효한 형식이어야 합니다.
노드(nodes)와 엣지(edges)를 포함한 완전한 LangFlow JSON 구조를 반환해야 합니다.
예시:
{
  "data": {
    "nodes": [
      {
        "id": "prompt_node_1",
        "type": "PromptNode",
        "position": {"x": 100, "y": 100},
        "data": {"node": {"template": {"_type": "PromptNode", "content": "Hello, {name}!"}}}
      },
      {
        "id": "llm_node_1",
        "type": "ChatInput",
        "position": {"x": 300, "y": 100},
        "data": {"node": {"template": {"_type": "ChatInput"}}}
      }
    ],
    "edges": [
      {"id": "edge_1", "source": "prompt_node_1", "target": "llm_node_1", "sourceHandle": null, "targetHandle": null}
    ]
  }
}
"""

    messages_for_llm = [
        {"role": "system", "content": system_prompt_content},
        {"role": "user", "content": f"다음 요청에 맞는 LangFlow를 생성해줘: {user_query}"}
    ]

    try:
        response = await llm_client.chat.completions.create(
            model=model_id,
            messages=messages_for_llm,
            response_format={"type": "json_object"}, # JSON 형식 강제
            temperature=0.7 # 창의적인 생성을 위해 temperature를 0.7로 설정
        )
        generated_json_str = response.choices[0].message.content
        
        # 생성된 JSON이 유효한지 확인 (선택 사항)
        json.loads(generated_json_str) 
        return generated_json_str
    except Exception as e:
        return json.dumps({"error": f"LangFlow JSON 생성 중 오류 발생: {e}"})

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

generate_langflow_tool_schema = {
    "type": "function",
    "function": {
        "name": "generate_langflow_workflow",
        "description": "사용자의 요청을 분석하여, 해당 기능을 수행하는 LangFlow 워크플로우의 JSON 정의를 생성합니다. 복잡한 데이터 처리, LLM 체인 구성, 외부 API 연동 등 새로운 워크플로우가 필요할 때 사용합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "생성할 LangFlow 워크플로우에 대한 상세한 설명 또는 요청 내용"}
            },
            "required": ["input"]
        }
    }
}

available_tools: List[Dict[str, Any]] = [visualize_tool_schema, generate_langflow_tool_schema]

# 도구 이름과 실제 함수를 매핑합니다.
tool_functions: Dict[str, callable] = {
    "visualize_conversation_as_langflow": run,
    "generate_langflow_workflow": generate_langflow_workflow_run
}