from typing import Dict, Any
from schemas import ChatState


# 예제 4: 사람 개입 (Human-in-the-Loop)
def human_approval_node(state: ChatState) -> Dict[str, Any]:
    """Pauses the graph to wait for human approval."""
    return {"messages": [{"role": "system", "content": "관리자 승인이 필요합니다. 계속하려면 승인 후 그래프를 재개해주세요."}]}