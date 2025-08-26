"""
LangGraph 그래프 구성을 담당하는 모듈입니다.
"Modal Context Protocol"에 따라 새로운 에이전트 그래프를 구성합니다.
"""

from langgraph.graph import StateGraph, END
from core.schemas import AgentState
from core.agent_nodes import tool_dispatcher_node
from core.models import model_registry

def build_agent_graph():
    """
    "Modal Context Protocol"을 사용하는 새로운 에이전트 그래프를 구성합니다.
    이 그래프는 OpenAI 함수 호출을 중심으로 하는 단일 노드를 가집니다.
    
    Returns:
        tuple: (compiled_agent, tool_descriptions, agent_model_id)
    """
    # 1. 모델 정보 정의 및 등록
    # TODO: 이 정보를 설정 파일로 분리하는 것을 고려
    AGENT_MODEL_ID = "ax4"
    model_registry.register_model(
        model_id="ax4",
        name="ax4",
        provider="sktax",
        description="Modal Context Protocol 기반의 차세대 CoE 에이전트"
    )

    # 2. 새로운 AgentState를 사용하여 그래프를 정의합니다.
    graph = StateGraph(AgentState)

    # 3. 핵심 로직을 담은 'tool_dispatcher_node'를 'agent'라는 이름으로 추가합니다.
    graph.add_node("agent", tool_dispatcher_node)

    # 4. 'agent' 노드를 그래프의 시작점으로 설정합니다.
    graph.set_entry_point("agent")
    
    # 5. 'agent' 노드가 작업을 완료하면 그래프를 종료합니다.
    graph.add_edge("agent", END)

    # 6. 그래프를 컴파일합니다.
    agent = graph.compile()
    
    # 7. main.py와의 호환성을 위해 빈 도구 설명과 모델 ID를 반환합니다.
    # 향후 이 부분은 동적으로 채워지도록 개선될 수 있습니다.
    tool_descriptions = [] 
    
    print("✅ Compiled new agent graph with 'tool_dispatcher_node'.")
    
    return agent, tool_descriptions, AGENT_MODEL_ID


def build_aider_agent_graph():
    """
    Aider 전용 에이전트 그래프를 빌드합니다.
    현재는 기본 에이전트와 동일한 그래프를 반환합니다.
    """
    print("⚠️ build_aider_agent_graph is using the default agent graph.")
    return build_agent_graph()
