"""
새로운 Modal Context Protocol 아키텍처의 핵심 노드를 정의합니다.
"""
import json
from typing import Dict, Any

from core.schemas import AgentState
from core.llm_client import get_client_for_model
from tools.registry import get_tools_for_mode, get_all_tool_functions

def tool_dispatcher_node(state: AgentState) -> Dict[str, Any]:
    """
    OpenAI 함수 호출을 관리하는 핵심 노드입니다.

    1. 현재 모드에 맞는 도구를 가져옵니다.
    2. LLM을 호출하여 함수 호출을 요청받습니다.
    3. 함수를 실행하고 결과를 다시 LLM에 전달하여 최종 응답을 받습니다.
    """
    # 상태에서 현재 모드, 대화 기록, 모델 ID를 가져옵니다.
    mode = state.get("mode", "basic") # 기본 모드를 'basic'으로 설정
    history = state["history"]
    # TODO: 모델 ID를 설정에서 동적으로 가져오도록 수정 필요
    model_id = "ax4"

    # 현재 모드에 맞는 도구 스키마를 가져옵니다.
    tool_schemas, _ = get_tools_for_mode(mode)
    all_tool_functions = get_all_tool_functions()
    
    # LLM 클라이언트를 가져옵니다.
    llm_client = get_client_for_model(model_id)

    # LLM을 호출합니다.
    print(f"--- Calling LLM (mode: {mode}) with {len(tool_schemas)} tools ---")
    response = llm_client.chat.completions.create(
        model=model_id,
        messages=history,
        tools=tool_schemas if tool_schemas else None,
        tool_choice="auto" if tool_schemas else None,
    )
    response_message = response.choices[0].message

    # LLM 응답을 기록에 추가합니다.
    # Pydantic 모델을 dict로 변환하여 history에 추가해야 합니다.
    history.append(response_message.model_dump())

    # 함수 호출이 있는지 확인하고 처리합니다.
    if response_message.tool_calls:
        print(f"--- LLM requested {len(response_message.tool_calls)} tool calls ---")
        
        # 요청된 모든 도구를 실행합니다.
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_to_call = all_tool_functions.get(function_name)
            
            if function_to_call:
                try:
                    function_args = json.loads(tool_call.function.arguments)
                    print(f"Executing tool: {function_name}({function_args})")
                    function_response = function_to_call(**function_args)
                    
                    # 실행 결과를 ToolMessage 형식으로 만들어 기록에 추가
                    history.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": str(function_response), # 결과는 항상 문자열로 변환
                    })
                except Exception as e:
                    print(f"Error executing tool {function_name}: {e}")
                    history.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": f"Error executing tool: {e}",
                    })
            else:
                print(f"Error: Tool '{function_name}' not found.")
                history.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": f"Error: Tool '{function_name}' not found.",
                })

        # 도구 실행 후, 다시 LLM을 호출하여 최종 응답을 생성합니다.
        print("--- Calling LLM again with tool results ---")
        second_response = llm_client.chat.completions.create(
            model=model_id,
            messages=history,
        )
        second_response_message = second_response.choices[0].message
        history.append(second_response_message.model_dump())

    # 최종 상태(업데이트된 history)를 반환합니다.
    return {"history": history}
