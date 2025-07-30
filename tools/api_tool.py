import requests
from typing import Dict, Any
from schemas import ChatState
from langgraph.graph import END

# 라우터 프롬프트에 사용될 도구 설명
api_tool_description = {
    "name": "api_call",
    "description": "외부 API를 호출하여 사용자 정보를 가져옵니다. (예: \"1번 사용자 정보 알려줘\")"
}

def after_api_call(state: ChatState) -> str:
    """
    라우터가 'combined_tool'을 선택했을 경우에만 'class_analysis'로 분기하고,
    단순 'api_call'의 경우에는 종료합니다.
    """
    return "class_analysis" if state.get("next_node") == "combined_tool" else END


def api_call_node(state: ChatState) -> Dict[str, Any]:
    """
    공개 REST API(JSONPlaceholder)를 호출하여 사용자 ID로 게시물 데이터를 가져옵니다.
    """
    user_content = state.get("original_input", "")
    user_id = ''.join(filter(str.isdigit, user_content))
    if not user_id:
        return {"messages": [{"role": "system", "content": "API 호출 오류: 사용자 ID를 찾을 수 없습니다."}]}
    
    try:
        response = requests.get(f"https://jsonplaceholder.typicode.com/posts/{user_id}")
        response.raise_for_status()
        data = response.json()
        return {"messages": [{"role": "assistant", "content": f"API 결과: {data['title']}"}], "api_data": data}
    except requests.RequestException as e:
        return {"messages": [{"role": "system", "content": f"API 호출 실패: {e}"}]}

# 그래프의 특별한 엣지(흐름)를 정의합니다.
api_tool_edges = [
    {
        "type": "conditional",
        "source": "api_call",
        "condition": after_api_call,
        "path_map": {"class_analysis": "class_analysis", END: END}
    }
]