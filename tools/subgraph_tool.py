from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from core.schemas import AgentState
from typing_extensions import TypedDict

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

async def run(tool_input: Optional[Dict[str, Any]], state: AgentState) -> Dict[str, Any]:
    """Invokes a compiled sub-graph to get a greeting message."""
    result = await compiled_sub_graph.ainvoke({})
    return {"messages": [{"role": "assistant", "content": result['greeting_message']}]}

# --- Tool Schemas and Functions for LLM ---

available_tools: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "sub_graph",
            "description": "인사를 처리합니다. (예: \"안녕\")",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        "url_path": "/tools/sub-graph"
    }
]

tool_functions: Dict[str, callable] = {
    "sub_graph": run
}