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
    front_tool_name은 UI 컨텍스트 식별자다. 
    -> 해당 컨텍스트에 맞는 도구 세트를 로드하고
    -> LLM이 실제 도구를 선택/호출하도록 한다.
    -> 선택된 '실제 도구 이름'으로만 실행한다.
    """
    import json
    import uuid
    import logging
    from core.llm_client import get_client_for_model, client as default_llm_client
    from services import tool_dispatcher

    logger = logging.getLogger(__name__)

    # ---- 상태 추출 ----
    front_tool_name = state.get("front_tool_name")
    tool_input = state.get("tool_input") or {}
    history = state["history"]
    model_id = state["model_id"]

    # front_tool_name을 실행 기준이 아닌 "컨텍스트"로만 사용
    context = front_tool_name or state.get("context") or "default"
    client_tools = state.get("tools", []) or []  # 클라이언트가 보낸 tool 스키마(있으면)

    # ---- 서버 도구 세트 로드 ----
    server_tool_schemas, server_tool_functions = tool_dispatcher.get_available_tools_for_context(context)
    client_tool_schemas = [t if isinstance(t, dict) else getattr(t, "model_dump", lambda **_: t)() for t in client_tools]
    combined_tool_schemas = client_tool_schemas + server_tool_schemas

    # LLM 클라이언트 선택
    llm_client = get_client_for_model(model_id)

    logger.info(
        f"--- Calling LLM with {len(combined_tool_schemas)} tools "
        f"({len(client_tool_schemas)} client, {len(server_tool_schemas)} server) for context '{context}' ---"
    )

    # tools/tool_choice에 None을 넣지 않도록 kwargs 동적 구성
    llm_kwargs = dict(model=model_id, messages=history)
    if combined_tool_schemas:
        llm_kwargs["tools"] = combined_tool_schemas
        llm_kwargs["tool_choice"] = "auto"

    response = llm_client.chat.completions.create(**llm_kwargs)
    response_message = response.choices[0].message
    history.append(response_message.model_dump())

    # 안전한 도구명/인자 추출기
    def _extract_tool_name(tc) -> str:
        try:
            # OpenAI SDK 객체
            return tc.function.name
        except Exception:
            # dict 형태
            fn = (tc.get("function") if isinstance(tc, dict) else None) or {}
            return fn.get("name")

    def _extract_tool_args(tc) -> dict:
        try:
            return json.loads(tc.function.arguments)
        except Exception:
            fn = (tc.get("function") if isinstance(tc, dict) else None) or {}
            args = fn.get("arguments") or "{}"
            try:
                return json.loads(args)
            except Exception:
                return {}

    # 서버 쪽에서 실행할 함수 맵
    all_server_funcs = server_tool_functions  # { tool_name: async_fn(tool_input, state) }

    # 도구 호출 처리
    tool_calls = getattr(response_message, "tool_calls", None)
    if not tool_calls and isinstance(response_message, dict):
        tool_calls = response_message.get("tool_calls")

    if tool_calls:
        logger.info(f"--- LLM requested {len(tool_calls)} tool calls ---")
        server_tool_executed = False

        # 서버에서 실행할 도구만 골라서 실행
        for tc in tool_calls:
            fn_name = _extract_tool_name(tc)
            if fn_name in all_server_funcs:
                server_tool_executed = True
                fn = all_server_funcs[fn_name]
                try:
                    fn_args = _extract_tool_args(tc)
                    logger.info(f"Executing server-side tool: {fn_name}({fn_args})")
                    result = await fn(tool_input=fn_args, state=state)
                    history.append({
                        "tool_call_id": getattr(tc, "id", tc.get("id") if isinstance(tc, dict) else None),
                        "role": "tool",
                        "name": fn_name,
                        "content": json.dumps(result, ensure_ascii=False),
                    })
                except Exception as e:
                    logger.error(f"Error executing server-side tool {fn_name}: {e}")
                    history.append({
                        "tool_call_id": getattr(tc, "id", tc.get("id") if isinstance(tc, dict) else None),
                        "role": "tool",
                        "name": fn_name,
                        "content": f"Error executing tool: {e}",
                    })
            # 클라이언트 도구는 이미 history에 tool_calls로 포함되어 있으므로 별도 처리 불필요

        # 서버 도구가 하나라도 실행된 경우에만 LLM을 다시 호출하여 결과 정제
        if server_tool_executed:
            logger.info("--- Calling LLM again with server-side tool results ---")
            second = default_llm_client.chat.completions.create(model=model_id, messages=history)
            history.append(second.choices[0].message.model_dump())

    return {"history": history}
