from typing import Dict, Any, TypedDict
from langgraph.graph import StateGraph, START, END
from core.schemas import ChatState

# 라우터 프롬프트에 사용될 도구 설명
subgraph_tool_description = {
    "name": "sub_graph",
    "description": "인사를 처리합니다. (예: \"안녕\")"
}


# 예제 3: 하위 LangGraph 호출
class GreetingState(TypedDict):
    greeting_message: str

def say_hello(state: GreetingState):
    return {"greeting_message": "안녕하세요! 무엇을 도와드릴까요?"}

greeting_sub_graph = StateGraph(GreetingState)
greeting_sub_graph.add_node("hello", say_hello)
greeting_sub_graph.add_edge(START, "hello")
greeting_sub_graph.add_edge("hello", END)
compiled_sub_graph = greeting_sub_graph.compile()

def sub_graph_node(state: ChatState) -> Dict[str, Any]:
    """Invokes a compiled sub-graph to get a greeting message."""
    result = compiled_sub_graph.invoke({})
    return {"messages": [{"role": "assistant", "content": result['greeting_message']}]}