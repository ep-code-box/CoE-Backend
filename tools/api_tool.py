import requests
from typing import Dict, Any
from schemas import ChatState


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