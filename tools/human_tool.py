from typing import Dict, Any
from core.schemas import ChatState
from .utils import find_last_user_message

# 라우터 프롬프트에 사용될 도구 설명
human_tool_descriptions = [
    {
        "name": "human_approval",
        "description": "사람의 승인이 필요한 작업을 요청합니다. (예: \"중요한 작업 승인해줘\")",
        "url_path": "/tools/human-approval"
    },
    {
        "name": "process_approval",
        "description": "사용자의 'approve' 또는 'reject' 응답을 처리합니다. 이 도구는 시스템이 승인을 요청한 직후에만 사용해야 합니다.",
        "url_path": "/tools/process-approval"
    }
]

# 예제 4: 사람 개입 (Human-in-the-Loop)
def human_approval_node(state: ChatState) -> Dict[str, Any]:
    """
    Pauses the graph to wait for human approval.
    It provides a more detailed message about what needs approval.
    """
    # 승인이 필요한 원본 요청을 가져옵니다.
    original_request = state.get("original_input", "알 수 없는 작업")
    
    # 사용자에게 승인을 요청하는 상세한 메시지를 생성합니다.
    approval_message = (
        f"'{original_request}' 작업에 대한 관리자 승인이 필요합니다. "
        "계속 진행하려면 'approve', 취소하려면 'reject'를 입력해주세요."
    )
    
    return {"messages": [{"role": "system", "content": approval_message}]}


def process_approval_node(state: ChatState) -> Dict[str, Any]:
    """
    Processes the human's response (approve/reject) after the interruption.
    """
    # 마지막 사용자 메시지(승인 또는 거절)를 가져옵니다.
    last_user_message = find_last_user_message(state["messages"])

    if last_user_message and 'approve' in last_user_message.lower():
        return {"messages": [{"role": "system", "content": "승인되었습니다. 요청된 작업을 계속 진행합니다."}]}
    else:
        return {"messages": [{"role": "system", "content": "거절되었습니다. 작업이 취소되었습니다."}]}

# 그래프의 특별한 엣지(흐름)를 정의합니다.
human_tool_edges = [
    {
        "type": "standard",
        "source": "human_approval",
        "target": "process_approval"
    }
]