"""
새로운 Modal Context Protocol 아키텍처의 핵심 노드를 정의합니다.
"""
import json
import uuid
from typing import Dict, Any

from core.schemas import AgentState, Tool
from core.llm_client import get_client_for_model, client as default_llm_client
from services import tool_dispatcher
import logging

logger = logging.getLogger(__name__)

async def tool_dispatcher_node(state: AgentState) -> Dict[str, Any]:
    """
    요청에 front_tool_name이 있는 경우(MCP) 해당 도구를 직접 실행하거나, 
    그렇지 않은 경우 LLM을 통해 함수 호출을 관리하는 핵심 노드입니다.
    """
    # 상태에서 필요한 정보들을 가져옵니다.
    front_tool_name = state.get("front_tool_name")
    tool_input = state.get("tool_input") or {}
    history = state["history"]
    model_id = state["model_id"]
    context = state.get("context", "default")
    client_tools = state.get("tools", []) or []

    # 1. MCP(Modal Context Protocol): front_tool_name이 명시적으로 제공된 경우
    if front_tool_name:
        logger.info(f"[MCP] Executing tool directly based on front_tool_name: {front_tool_name}")

        # 1.1. 서버 측 도구인지 확인하고 실행
        server_tool_path = tool_dispatcher.find_python_tool_path(front_tool_name)
        if server_tool_path:
            logger.info(f"[MCP] Found server-side tool: {front_tool_name}")
            tool_result = await tool_dispatcher.run_python_tool(server_tool_path, tool_input, state)
            
            # LLM을 통해 사용자 친화적인 응답 생성 (기본 클라이언트 사용)
            refinement_prompt = [
                *history,
                {"role": "system", "content": f"You are a helpful assistant. The user requested to run the tool '{front_tool_name}' and got the following result. Please present this result to the user in a clear and friendly way."},
                {"role": "user", "content": f"Tool '{front_tool_name}' execution result:\n\n{str(tool_result)}"}
            ]
            response = default_llm_client.chat.completions.create(model=model_id, messages=refinement_prompt)
            final_message = response.choices[0].message.model_dump()
            history.append(final_message)
            return {"history": history}

        # 1.2. 클라이언트 측 도구인지 확인하고 실행 요청
        is_client_tool = any(tool.function.name == front_tool_name for tool in client_tools)
        if is_client_tool:
            logger.info(f"[MCP] Found client-side tool: {front_tool_name}. Emitting tool_call for client execution.")
            tool_call_id = f"call_{uuid.uuid4().hex}"
            arguments_str = json.dumps(tool_input)
            
            tool_call_message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": tool_call_id,
                    "type": "function",
                    "function": {"name": front_tool_name, "arguments": arguments_str},
                }],
            }
            history.append(tool_call_message)
            return {"history": history}

        # 1.3. 도구를 찾지 못한 경우, 일반 채팅으로 fallback
        logger.warning(f"[MCP] Tool '{front_tool_name}' not found on server or client. Falling back to general chat.")

    # 2. 일반 채팅: LLM이 도구를 선택하도록 로직 수행
    logger.info(f"No front_tool_name provided. Proceeding with LLM-based tool calling for context: '{context}'")
    
    # 서버 측 동적 도구와 클라이언트 측 도구를 병합합니다.
    server_tool_schemas, server_tool_functions = tool_dispatcher.get_available_tools_for_context(context)
    client_tool_schemas = [tool.model_dump(exclude_none=True) for tool in client_tools]
    combined_tool_schemas = client_tool_schemas + server_tool_schemas
    all_tool_functions = server_tool_functions # 클라이언트 측 함수는 클라이언트가 직접 실행

    # LLM 호출 시에는 특정 프로바이더의 클라이언트를 사용해야 합니다.
    # 여기서는 상태에 있는 model_id를 기반으로 클라이언트를 가져옵니다.
    llm_client = get_client_for_model(model_id)

    logger.info(f"--- Calling LLM with {len(combined_tool_schemas)} tools ({len(client_tool_schemas)} client, {len(server_tool_schemas)} server) for context '{context}' ---")
    response = llm_client.chat.completions.create(
        model=model_id,
        messages=history,
        tools=combined_tool_schemas if combined_tool_schemas else None,
        tool_choice="auto" if combined_tool_schemas else None,
    )
    response_message = response.choices[0].message
    history.append(response_message.model_dump())

    if response_message.tool_calls:
        logger.info(f"--- LLM requested {len(response_message.tool_calls)} tool calls ---")
        
        # 서버에서 실행해야 할 도구만 필터링
        server_tool_calls = [
            tc for tc in response_message.tool_calls 
            if tc.function.name in all_tool_functions
        ]
        
        # 서버 도구 실행 및 결과 추가
        if server_tool_calls:
            for tool_call in server_tool_calls:
                function_name = tool_call.function.name
                function_to_call = all_tool_functions.get(function_name)
                try:
                    function_args = json.loads(tool_call.function.arguments)
                    logger.info(f"Executing server-side tool: {function_name}({function_args})")
                    # 'run' 함수 시그니처에 맞게 tool_input과 state를 전달합니다.
                    function_response = await function_to_call(tool_input=function_args, state=state)
                    history.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": str(function_response),
                    })
                except Exception as e:
                    logger.error(f"Error executing server-side tool {function_name}: {e}")
                    history.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": f"Error executing tool: {e}",
                    })
            
            # 서버 도구 실행 결과가 반영된 history로 다시 LLM 호출 (기본 클라이언트 사용)
            logger.info("--- Calling LLM again with server-side tool results ---")
            second_response = default_llm_client.chat.completions.create(
                model=model_id,
                messages=history,
            )
            second_response_message = second_response.choices[0].message
            history.append(second_response_message.model_dump())

    return {"history": history}
