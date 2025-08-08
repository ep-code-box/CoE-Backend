"""
LangGraph 그래프 구성을 담당하는 모듈입니다.
도구 레지스트리에서 로드한 노드들을 기반으로 그래프를 동적으로 구성합니다.
"""

from langgraph.graph import StateGraph, START, END
from core.schemas import ChatState
from tools.registry import load_all_tools
from routers.router import router_node
from core.models import model_registry
from core.tool_wrapper import wrap_all_tools


def build_agent_graph():
    """
    도구 레지스트리를 통해 모든 노드, 설명, 엣지를 동적으로 로드하고
    LangGraph를 구성하여 컴파일된 에이전트를 반환합니다.
    
    Returns:
        tuple: (compiled_agent, tool_descriptions, agent_model_id)
    """
    # 1) 도구 레지스트리를 통해 모든 노드, 설명, 엣지를 동적으로 로드
    all_nodes, all_tool_descriptions, all_special_edges = load_all_tools()
    
    # 2) 모든 도구 노드에 실행 로깅 래퍼 적용
    all_nodes = wrap_all_tools(all_nodes)

    # 'end' 도구에 대한 설명 추가
    all_tool_descriptions.append({
        "name": "end",
        "description": "사용자가 대화를 끝내고 싶어할 때 사용합니다."
    })

    # 3) 라우터가 사용할 유효한 도구 이름 목록 및 OpenWebUI 연동을 위한 에이전트 모델 정의
    VALID_TOOL_NAMES = [tool['name'] for tool in all_tool_descriptions]
    AGENT_MODEL_ID = "coe-agent-v1"  # OpenWebUI에서 사용할 모델 ID

    # 에이전트를 모델 레지스트리에 동적으로 등록
    model_registry.register_model(
        model_id=AGENT_MODEL_ID,
        name="CoE Agent v1",  # OpenWebUI에 표시될 이름
        provider="CoE",
        description="CoE LangGraph Agent for development guide extraction"
    )

    # 4) 그래프 구성 및 컴파일 (모든 노드와 엣지 추가)
    graph = StateGraph(ChatState)

    # 라우터 노드 추가 (유효한 도구 이름 목록을 전달)
    def configured_router_node(state: ChatState) -> dict:
        return router_node(state, all_tool_descriptions, model_id="ax4")
    
    graph.add_node("router", configured_router_node)

    # 레지스트리에서 로드한 모든 도구 노드를 동적으로 추가
    for name, node_func in all_nodes.items():
        graph.add_node(name, node_func)

    # 그래프의 시작점을 라우터로 설정
    graph.set_entry_point("router")

    # 라우터의 결정에 따라 다음 노드로 분기하도록 동적으로 엣지 매핑 생성
    routable_tool_names = [tool['name'] for tool in all_tool_descriptions if tool['name'] != 'end']
    edge_mapping = {name: name for name in routable_tool_names}
    edge_mapping["combined_tool"] = "api_call"  # 'combined_tool'은 'api_call'로 시작하는 특별 케이스
    edge_mapping["end"] = END
    edge_mapping["error"] = END

    graph.add_conditional_edges(
        "router",
        lambda state: state["next_node"],
        edge_mapping
    )

    # 레지스트리에서 로드한 특별한 엣지들을 동적으로 추가
    special_edge_sources = set()
    for edge_config in all_special_edges:
        source_node = edge_config["source"]
        special_edge_sources.add(source_node)
        if edge_config["type"] == "conditional":
            graph.add_conditional_edges(
                source_node,
                edge_config["condition"],
                edge_config["path_map"]
            )
        elif edge_config["type"] == "standard":
            graph.add_edge(source_node, edge_config["target"])

    # 특별한 엣지가 정의된 노드와 라우터를 제외한 나머지 모든 노드는 작업 완료 후 종료(END)로 연결
    nodes_with_special_outgoing_edges = special_edge_sources.union({"router"})
    for node_name in all_nodes:
        if node_name not in nodes_with_special_outgoing_edges:
            graph.add_edge(node_name, END)

    # 그래프 컴파일
    agent = graph.compile(interrupt_after=["human_approval"])
    
    return agent, all_tool_descriptions, AGENT_MODEL_ID


def build_aider_agent_graph():
    """
    Aider 전용 에이전트 그래프를 빌드합니다.
    ax4 모델을 사용하고, 등록된 모든 도구를 활용합니다.
    
    Returns:
        tuple: (compiled_agent, tool_descriptions, agent_model_id)
    """
    # 1) 도구 레지스트리를 통해 모든 노드, 설명, 엣지를 동적으로 로드
    all_nodes, all_tool_descriptions, all_special_edges = load_all_tools()
    
    # 2) 모든 도구 노드에 실행 로깅 래퍼 적용
    all_nodes = wrap_all_tools(all_nodes)

    # 'end' 도구에 대한 설명 추가
    all_tool_descriptions.append({
        "name": "end",
        "description": "사용자가 대화를 끝내고 싶어할 때 사용합니다."
    })

    # 3) 라우터가 사용할 유효한 도구 이름 목록 및 OpenWebUI 연동을 위한 에이전트 모델 정의
    VALID_TOOL_NAMES = [tool['name'] for tool in all_tool_descriptions]
    AGENT_MODEL_ID = "aider-agent-model"

    # 에이전트를 모델 레지스트리에 동적으로 등록
    model_registry.register_model(
        model_id=AGENT_MODEL_ID,
        name="Aider Agent",
        provider="CoE",
        description="CoE LangGraph Agent for aider with ax4"
    )

    # 4) 그래프 구성 및 컴파일 (모든 노드와 엣지 추가)
    graph = StateGraph(ChatState)

    # 라우터 노드 추가 (유효한 도구 이름 목록을 전달)
    def configured_router_node(state: ChatState) -> dict:
        return router_node(state, all_tool_descriptions, model_id="ax4")
    
    graph.add_node("router", configured_router_node)

    # 레지스트리에서 로드한 모든 도구 노드를 동적으로 추가
    for name, node_func in all_nodes.items():
        graph.add_node(name, node_func)

    # 그래프의 시작점을 라우터로 설정
    graph.set_entry_point("router")

    # 라우터의 결정에 따라 다음 노드로 분기하도록 동적으로 엣지 매핑 생성
    routable_tool_names = [tool['name'] for tool in all_tool_descriptions if tool['name'] != 'end']
    edge_mapping = {name: name for name in routable_tool_names}
    edge_mapping["combined_tool"] = "api_call"
    edge_mapping["end"] = END
    edge_mapping["error"] = END

    graph.add_conditional_edges(
        "router",
        lambda state: state["next_node"],
        edge_mapping
    )

    # 레지스트리에서 로드한 특별한 엣지들을 동적으로 추가
    special_edge_sources = set()
    for edge_config in all_special_edges:
        source_node = edge_config["source"]
        special_edge_sources.add(source_node)
        if edge_config["type"] == "conditional":
            graph.add_conditional_edges(
                source_node,
                edge_config["condition"],
                edge_config["path_map"]
            )
        elif edge_config["type"] == "standard":
            graph.add_edge(source_node, edge_config["target"])

    # 특별한 엣지가 정의된 노드와 라우터를 제외한 나머지 모든 노드는 작업 완료 후 종료(END)로 연결
    nodes_with_special_outgoing_edges = special_edge_sources.union({"router"})
    for node_name in all_nodes:
        if node_name not in nodes_with_special_outgoing_edges:
            graph.add_edge(node_name, END)

    # 그래프 컴파일
    agent = graph.compile(interrupt_after=["human_approval"])
    
    return agent, all_tool_descriptions, AGENT_MODEL_ID