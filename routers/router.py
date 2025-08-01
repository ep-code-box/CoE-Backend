"""
라우터 노드 로직을 담당하는 모듈입니다.
사용자의 요청에 가장 적합한 도구를 선택하는 역할을 합니다.
"""

import json
from typing import List, Dict, Any
from core.schemas import ChatState
from core.llm_client import client, default_model
from tools.utils import find_last_user_message


def router_node(state: ChatState, tool_descriptions: List[Dict[str, Any]]) -> dict:
    """
    사용자의 요청에 가장 적합한 도구를 선택하는 라우터 노드입니다.
    
    Args:
        state: 현재 채팅 상태
        tool_descriptions: 사용 가능한 도구들의 설명 목록
        
    Returns:
        dict: 업데이트된 상태 정보
    """
    # 마지막 사용자 메시지를 original_input에 저장
    last_user_message = find_last_user_message(state["messages"])
    
    # 유효한 도구 이름 목록 생성
    VALID_TOOL_NAMES = [tool['name'] for tool in tool_descriptions]
    
    # 동적으로 도구 설명 목록 생성
    tool_descriptions_string = "\n".join(
        [f"- '{tool['name']}': {tool['description']}" for tool in tool_descriptions]
    )
    
    # 시스템 프롬프트 구성
    system_prompt = f"""사용자의 요청에 가장 적합한 도구를 다음 중에서 선택하세요.
{tool_descriptions_string}

특별 규칙:
- 만약 바로 이전의 시스템 메시지가 승인을 요청하는 내용이고 사용자가 'approve' 또는 'reject'와 유사한 응답을 했다면, 반드시 'process_approval' 도구를 선택해야 합니다.

응답은 반드시 다음 JSON 형식이어야 합니다: {{"next_tool": "선택한 도구"}}"""

    prompt_messages = state["messages"] + [
        {"role": "system", "content": system_prompt}
    ]
    
    try:
        resp = client.chat.completions.create(
            model=default_model.model_id,  # 기본 모델 ID 사용
            messages=prompt_messages,
            response_format={"type": "json_object"}  # JSON 모드 활성화
        )
        # OpenAI 객체를 dict로 변환하여 타입 일관성 유지
        response_message = resp.choices[0].message.model_dump()

        try:
            # LLM 응답(JSON) 파싱
            choice_json = json.loads(response_message["content"])
            choice = choice_json.get("next_tool")
            print(f"🤖[Router]: LLM이 선택한 도구: {choice}")
            
            if choice not in VALID_TOOL_NAMES:  # 유효한 도구 이름 목록으로 검사
                raise ValueError(f"LLM이 유효하지 않은 도구({choice})를 반환했습니다.")
            
            # 다음 노드를 상태에 저장하고, LLM의 응답도 기록에 추가
            return {
                "messages": [response_message], 
                "next_node": choice, 
                "original_input": last_user_message
            }
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # 파싱 실패 시 오류 메시지를 기록하고 그래프 종료
            error_msg = f"라우터가 LLM 응답을 파싱하는 데 실패했습니다: {e}"
            print(f"🤖[Router]: Error - {error_msg}")
            return {
                "messages": [response_message, {"role": "system", "content": error_msg}], 
                "next_node": "error"
            }

    except Exception as e:
        # API 호출 실패 시 오류 메시지를 기록하고 그래프 종료
        error_msg = f"라우터 API 호출에 실패했습니다: {e}"
        print(f"🤖[Router]: Error - {error_msg}")
        return {
            "messages": [{"role": "system", "content": error_msg}], 
            "next_node": "error"
        }