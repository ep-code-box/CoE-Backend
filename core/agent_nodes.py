"""
새로운 Modal Context Protocol 아키텍처의 핵심 노드를 정의합니다.
"""
import json
import uuid
from typing import Dict, Any, List, Optional, Set

from core.schemas import AgentState, Tool
from core.llm_client import get_client_for_model, client as default_llm_client
from services import tool_dispatcher
import logging

logger = logging.getLogger(__name__)

async def tool_dispatcher_node(state: AgentState) -> Dict[str, Any]:
    """
    context는 UI 컨텍스트 식별자다.
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
    tool_input = state.get("tool_input") or {}
    history = state["history"]
    model_id = state["model_id"]

    # context를 실행 기준으로 사용
    context = state.get("context") or "default"
    # chat_api에서 병합된 도구 목록
    resolved_tools = state.get("tools", []) or [] 

    # ---- 서버 도구 함수 로드 ----
    # 스키마는 이미 chat_api에서 병합되었으므로, 여기서는 실행할 함수만 가져온다.
    group_name = state.get("group_name") if isinstance(state, dict) else None
    _schemas, server_tool_functions = tool_dispatcher.get_available_tools_for_context(
        context,
        group_name,
    )
    
    # Pydantic 모델을 dict로 변환
    combined_tool_schemas = [t if isinstance(t, dict) else t.model_dump(exclude_none=True) for t in resolved_tools]

    auto_route_suggestion = None
    forced_tool_choice: Optional[Dict[str, Any]] = None

    # 자동 라우팅(설명 기반/LLM 기반): 최근 사용자 메시지를 분석하여 사전 선택한 도구를 제안
    try:
        last_user = None
        for msg in reversed(history):
            if (isinstance(msg, dict) and msg.get("role") == "user") or getattr(msg, "role", None) == "user":
                last_user = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
                break
        if last_user:
            # Evaluate tools via strategy (LLM intent by default, fallback to text)
            auto_route_suggestion = await tool_dispatcher.maybe_execute_best_tool(
                last_user, context, state
            )
    except Exception as e:
        logger.warning(f"Auto-routing check failed: {e}")

    # LLM 클라이언트 선택
    llm_client = get_client_for_model(model_id)

    # LLM 호출 메시지 구성 (필요 시 자동 라우터 힌트 추가)
    messages_for_llm: List[Dict[str, Any]] = list(history)

    available_tool_names: Set[str] = set()
    for schema in combined_tool_schemas:
        try:
            fn = (schema.get("function") if isinstance(schema, dict) else {}) or {}
            name = fn.get("name")
            if name:
                available_tool_names.add(name)
        except Exception:
            continue

    if auto_route_suggestion:
        suggested_tool = auto_route_suggestion.get("tool_name")
        if suggested_tool and suggested_tool in available_tool_names:
            forced_tool_choice = {"type": "function", "function": {"name": suggested_tool}}
            instruction_lines = [
                "Auto router selected a tool for this request.",
                f"Tool: {suggested_tool}",
                "You must call this tool once before producing a final reply.",
            ]
            reason = auto_route_suggestion.get("reason")
            if reason:
                instruction_lines.append(f"Selection hint: matched keyword '{reason}'.")
            if auto_route_suggestion.get("tool_type") == "flow":
                flow_name = auto_route_suggestion.get("flow_name")
                if flow_name:
                    instruction_lines.append(
                        f"Execute LangFlow '{flow_name}' via execute_langflow."
                    )
            suggested_args = auto_route_suggestion.get("arguments")
            if suggested_args:
                try:
                    instruction_lines.append(
                        "Use the following JSON arguments for the call: "
                        + json.dumps(suggested_args, ensure_ascii=False)
                    )
                except Exception:
                    pass
            instruction_lines.append("After the tool call, summarize the result for the user.")
            messages_for_llm.append({"role": "system", "content": "\n".join(instruction_lines)})
            logger.info(
                "Auto-router suggestion accepted: tool=%s source=%s",
                suggested_tool,
                auto_route_suggestion.get("source"),
            )
        elif suggested_tool:
            logger.info(
                "Auto-router suggestion skipped because tool '%s' is not in the available tool list.",
                suggested_tool,
            )

    logger.info(
        f"--- Calling LLM with {len(combined_tool_schemas)} tools for context '{context}' ---"
    )

    # tools/tool_choice에 None을 넣지 않도록 kwargs 동적 구성
    llm_kwargs = dict(model=model_id, messages=messages_for_llm)
    if combined_tool_schemas:
        llm_kwargs["tools"] = combined_tool_schemas
        if forced_tool_choice is not None:
            llm_kwargs["tool_choice"] = forced_tool_choice
        else:
            llm_kwargs["tool_choice"] = "auto"

    response = await llm_client.chat.completions.create(**llm_kwargs)
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
        has_client_tool_call = False  # 클라이언트 도구 호출 여부 플래그

        # 서버에서 실행할 도구와 클라이언트 도구를 구분하여 처리
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
            else:
                # 클라이언트 도구 호출이 있으면 플래그 설정
                has_client_tool_call = True
                logger.info(f"Client-side tool requested: {fn_name}. Deferring to client.")

        # 서버 도구가 실행되었고, 클라이언트 도구 호출이 없는 경우에만 LLM을 다시 호출
        if server_tool_executed and not has_client_tool_call:
            logger.info("--- Calling LLM again with server-side tool results ---")
            second = await default_llm_client.chat.completions.create(model=model_id, messages=history)
            history.append(second.choices[0].message.model_dump())

    return {"history": history}
