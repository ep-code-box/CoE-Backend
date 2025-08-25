"""
새로운 Modal Context Protocol 아키텍처의 핵심 노드를 정의합니다.
"""
import json
from typing import Dict, Any

from core.schemas import AgentState
from core.llm_client import get_client_for_model
from services import tool_dispatcher
import logging

logger = logging.getLogger(__name__)

async def tool_dispatcher_node(state: AgentState) -> Dict[str, Any]:
    """
    요청에 front_tool_name이 있는 경우 해당 도구를 직접 실행하고, 그렇지 않은 경우 LLM을 통해 함수 호출을 관리하는 핵심 노드입니다.
    """
    # 상태에서 필요한 정보들을 가져옵니다.
    front_tool_name = state.get("front_tool_name")
    tool_input = state.get("tool_input")
    history = state["history"]
    model_id = state["model_id"]
    context = state.get("context", "default") # 컨텍스트가 없으면 'default' 사용

    # 1. front_tool_name이 제공된 경우, 직접 도구 실행
    if front_tool_name:
        logger.info(f"Executing tool directly based on front_tool_name: {front_tool_name}")
        tool_result = await tool_dispatcher.dispatch_and_execute(front_tool_name, tool_input, state)

        # 1.1. 도구를 성공적으로 찾아 실행한 경우
        if tool_result is not None:
            # 도구 실행 결과를 LLM에 전달하여 사용자 친화적인 응답 생성
            llm_client = get_client_for_model(model_id)
            refinement_prompt = [
                *history,
                {
                    "role": "system",
                    "content": f"You are a helpful assistant. The user requested to run the tool '{front_tool_name}' and got the following result. Please present this result to the user in a clear and friendly way."
                },
                {
                    "role": "user",
                    "content": f"Tool '{front_tool_name}' execution result:\n\n{str(tool_result)}"
                }
            ]

            logger.info("Calling LLM to refine the tool result.")
            response = llm_client.chat.completions.create(
                model=model_id,
                messages=refinement_prompt,
            )
            final_message = response.choices[0].message.model_dump()
            history.append(final_message)
            return {"history": history}

        # 1.2. front_tool_name에 해당하는 도구를 찾지 못한 경우, 일반 채팅으로 fallback
        else:
            logger.info(f"Tool '{front_tool_name}' not found. Falling back to general chat.")
            # 이 경우, 아래의 일반 LLM 호출 로직을 그대로 따릅니다.

    # 2. front_tool_name이 없는 경우, 컨텍스트에 맞는 도구를 LLM이 선택하도록 로직 수행
    logger.info(f"No front_tool_name provided. Proceeding with LLM-based tool calling for context: '{context}'")
    tool_schemas, all_tool_functions = tool_dispatcher.get_available_tools_for_context(context)
    llm_client = get_client_for_model(model_id)

    print(f"--- Calling LLM with {len(tool_schemas)} tools for context '{context}' ---")
    response = llm_client.chat.completions.create(
        model=model_id,
        messages=history,
        tools=tool_schemas if tool_schemas else None,
        tool_choice="auto" if tool_schemas else None,
    )
    response_message = response.choices[0].message
    history.append(response_message.model_dump())

    if response_message.tool_calls:
        print(f"--- LLM requested {len(response_message.tool_calls)} tool calls ---")
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_to_call = all_tool_functions.get(function_name)
            
            if function_to_call:
                try:
                    function_args = json.loads(tool_call.function.arguments)
                    print(f"Executing tool: {function_name}({function_args})")
                    function_response = await function_to_call(**function_args)
                    history.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": str(function_response),
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

        print("--- Calling LLM again with tool results ---")
        second_response = llm_client.chat.completions.create(
            model=model_id,
            messages=history,
        )
        second_response_message = second_response.choices[0].message
        history.append(second_response_message.model_dump())

    return {"history": history}
