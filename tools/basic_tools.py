from typing import Dict, Any
from core.schemas import ChatState
from .utils import find_last_user_message

# 라우터 프롬프트에 사용될 도구 설명
basic_tool_descriptions = [
    {
        "name": "tool1",
        "description": "텍스트를 대문자로 변환합니다."
    },
    {
        "name": "tool2",
        "description": "텍스트를 역순으로 변환합니다."
    }
]


def tool1_node(state: ChatState) -> Dict[str, Any]:
    """Converts the last user message to uppercase."""
    user_content = find_last_user_message(state["messages"])
    if user_content:
        return {"messages": [{"role": "assistant", "content": user_content.upper()}]}
    return {"messages": [{"role": "system", "content": "Tool1 Error: User message not found."}]}

def tool2_node(state: ChatState) -> Dict[str, Any]:
    """Reverses the last user message."""
    user_content = find_last_user_message(state["messages"])
    if user_content:
        return {"messages": [{"role": "assistant", "content": user_content[::-1]}]}
    return {"messages": [{"role": "system", "content": "Tool2 Error: User message not found."}]}