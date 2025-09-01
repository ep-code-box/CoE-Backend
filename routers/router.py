"""
라우터 노드 로직을 담당하는 모듈입니다.
사용자의 요청에 가장 적합한 도구를 선택하는 역할을 합니다.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from core.schemas import ChatState
from core.llm_client import client, default_model
from tools.core.utils import extract_git_url, find_last_user_message

logger = logging.getLogger(__name__)


def router_node(state: ChatState, tool_descriptions: List[Dict[str, Any]], model_id: Optional[str] = None) -> dict:
    
    """
    사용자의 요청에 가장 적합한 도구를 선택하는 라우터 노드입니다.
    
    Args:
        state: 현재 채팅 상태
        tool_descriptions: 사용 가능한 도구들의 설명 목록
        model_id: 라우팅에 사용할 LLM 모델 ID (선택 사항). 제공되지 않으면 기본 모델 사용.
        
    Returns:
        dict: 업데이트된 상태 정보
    """
    # 마지막 사용자 메시지를 original_input에 저장
    last_user_message = find_last_user_message(state["messages"])
    
    # 유효한 도구 이름 목록 생성
    VALID_TOOL_NAMES = [tool['name'] for tool in tool_descriptions]
    
    # --- 강제 도구 선택 로직 (Pre-processing) ---
    # Git Repository URL과 개발 가이드 관련 키워드 조합 시 guide_extraction 강제 선택
    git_url = extract_git_url(last_user_message)
    dev_guide_keywords = ["개발가이드", "표준개발가이드", "공통코드화", "공통함수", "가이드"]
    
    if git_url and any(keyword in last_user_message for keyword in dev_guide_keywords):
        print(f"🤖[Router]: Forcing selection of 'guide_extraction' due to Git URL and dev guide keywords.")
        return {
            "messages": [], 
            "next_node": "guide_extraction", 
            "original_input": last_user_message
        }
    # --- 강제 도구 선택 로직 끝 ---

    # 동적으로 도구 설명 목록 생성
    tool_descriptions_string = "\n".join(
        [f"- '{tool['name']}': {tool['description']}" for tool in tool_descriptions]
    )
    
    # 시스템 프롬프트 구성
    system_prompt = f"""당신은 사용자의 요청을 분석하여 가장 적합한 도구를 선택하는 AI 라우터입니다.
사용 가능한 도구 목록과 각 도구의 설명을 참고하여, 사용자의 의도를 정확하게 파악하고 적절한 도구를 선택해주세요.

--- 사용 가능한 도구 ---
{tool_descriptions_string}

--- 특별 규칙 ---
1. **사용자의 요청에 Git Repository URL (예: https://github.com/...)이 명시적으로 포함되어 있고, '개발 가이드', '표준 개발 가이드', '공통 코드화', '공통 함수' 등과 관련된 내용이 있다면, 다른 어떤 도구보다 우선하여 반드시 'guide_extraction' 도구를 선택해야 합니다.**
2. 만약 바로 이전의 시스템 메시지가 승인을 요청하는 내용이고 사용자가 'approve' 또는 'reject'와 유사한 응답을 했다면, 반드시 'process_approval' 도구를 선택해야 합니다.
3. 그 외 사용자의 요청에 URL이 포함되어 있고, 해당 URL의 내용을 분석하거나 특정 정보를 추출하는 것이 목적이라면, URL을 처리할 수 있는 도구를 우선적으로 고려하세요.
4. 사용자의 입력에서 URL을 주의 깊게 찾아내고, 해당 URL이 어떤 도구와 관련될 수 있는지 판단하세요.

응답은 반드시 다음 JSON 형식이어야 합니다: {{'next_tool': '선택한 도구'}} """  

    prompt_messages = state["messages"] + [
        {"role": "system", "content": system_prompt}
    ]
    
    try:
        # 사용할 모델 ID 결정
        llm_model_id = model_id if model_id else default_model.model_id
        
        resp = client.chat.completions.create(
            model=llm_model_id,  # 동적으로 결정된 모델 ID 사용
            messages=prompt_messages,
            response_format={"type": "json_object"}  # JSON 모드 활성화
        )
        # OpenAI 객체를 dict로 변환하여 타입 일관성 유지
        response_message = resp.choices[0].message.model_dump()


        try:
            # LLM 응답(JSON) 파싱
            choice_json = json.loads(response_message["content"])
            choice = choice_json.get("next_tool")
            
            # 도구 선택 로그 추가 (전용 로거 사용)
            tool_logger = logging.getLogger("tool_tracker")
            tool_logger.info(f"TOOL_SELECTED: '{choice}' | USER_INPUT: '{last_user_message[:100]}{'...' if len(last_user_message) > 100 else ''}'")
            logger.info(f"🔧 [TOOL_SELECTION] Router selected tool: '{choice}' for user input: '{last_user_message[:100]}{'...' if len(last_user_message) > 100 else ''}'")
            print(f"🤖[Router]: LLM이 선택한 도구: {choice}")
            
            # 대화 이력에 도구 선택 정보 저장
            tool_context = state.get("_tool_context", {})
            session_id = tool_context.get("session_id")
            chat_service = tool_context.get("chat_service")
            turn_number = tool_context.get("turn_number", 1)
            
            if chat_service and session_id:
                try:
                    chat_service.save_chat_message(
                        session_id=session_id,
                        role="system",
                        content=f"[도구 선택] '{choice}' 도구가 선택되었습니다. 사용자 입력: {last_user_message[:100]}{'...' if len(last_user_message) > 100 else ''}",
                        turn_number=turn_number,
                        selected_tool=choice,
                        tool_metadata={
                            "selection_reason": "LLM 라우터에 의한 자동 선택",
                            "user_input_preview": last_user_message[:100] if last_user_message else None
                        }
                    )
                except Exception as db_error:
                    logger.warning(f"도구 선택 정보 저장 실패: {db_error}")
            
            if choice not in VALID_TOOL_NAMES:  # 유효한 도구 이름 목록으로 검사
                logger.error(f"🚨 [TOOL_SELECTION_ERROR] Invalid tool selected: '{choice}'. Valid tools: {VALID_TOOL_NAMES}")
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
            logger.error(f"🚨 [TOOL_SELECTION_ERROR] Router parsing failed: {error_msg}")
            print(f"🤖[Router]: Error - {error_msg}")
            return {
                "messages": [response_message, {"role": "system", "content": error_msg}], 
                "next_node": "error"
            }

    except Exception as e:
        # API 호출 실패 시 오류 메시지를 기록하고 그래프 종료
        error_msg = f"라우터 API 호출에 실패했습니다: {e}"
        logger.error(f"🚨 [TOOL_SELECTION_ERROR] Router API call failed: {error_msg}")
        print(f"🤖[Router]: Error - {error_msg}")
        return {
            "messages": [{"role": "system", "content": error_msg}], 
            "next_node": "error"
        }
