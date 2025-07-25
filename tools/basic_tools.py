from typing import Dict, Any
from schemas import ChatState
from .utils import find_last_user_message


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