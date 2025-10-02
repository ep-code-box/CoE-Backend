"""
채팅 관련 API 엔드포인트들을 담당하는 모듈입니다.

리팩토링 핵심
- context(프론트 UI 구분자)에 맞춰 서버 도구 세트를 로드(get_available_tools_for_context)
- 클라이언트 제공 tools와 병합 후 LangGraph Agent에 전달
- LLM 프록시 호출 시 tools/tool_choice의 None 제거 및 교차 검증 (타사 OpenAI 호환 게이트웨이 400 방지)
- BadRequest는 가능하면 400으로 패스스루, 기타 예외는 500
"""

import os
import time
import uuid
import logging
import httpx
import re
from datetime import datetime
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.schemas import OpenAIChatRequest, AgentState
from core.llm_client import get_client_for_model, get_model_info
from core.database import get_db
from services.chat_service import get_chat_service, ChatService
from services.pii_service import scrub_text

PII_BLOCK_MESSAGE = "고객 정보 또는 민감한 데이터가 확인되었습니다. 다시 질문 부탁드립니다."
from utils.streaming_utils import agent_stream_generator, proxy_stream_generator
from core.guide_agent.agent import GuideAgent
from core.guide_agent.formatter import format_result_as_markdown
from core.guide_agent.rag_client import RagClient
from services import tool_dispatcher

# (선택) OpenAI SDK BadRequest 패스스루용
try:
    import openai  # type: ignore
    OPENAI_IMPORTED = True
except Exception:
    OPENAI_IMPORTED = False

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

router = APIRouter(tags=["🤖 AI Chat"], prefix="/v1")

_agent_instance = None


# -----------------------------
# Agent 정보 등록/조회
# -----------------------------
def set_agent_info(agent, agent_model_id: str):
    global _agent_instance
    _agent_instance = {"agent": agent, "model_id": agent_model_id}


async def get_agent_info():
    if _agent_instance is None:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    return _agent_instance


# -----------------------------
# 유틸
# -----------------------------
def _drop_none_fields(d: Dict[str, Any]) -> Dict[str, Any]:
    """dict에서 None 값 키 제거"""
    return {k: v for k, v in d.items() if v is not None}


def _tool_key_for_merge(t: Any) -> str:
    """
    도구 중복 제거 키 생성:
    - pydantic 객체: name 속성
    - OpenAI tools(dict): function.name
    - dict에 name: 그 값
    - 그 외: id(t)
    """
    try:
        if hasattr(t, "name"):
            return getattr(t, "name")
        if isinstance(t, dict):
            if "function" in t and isinstance(t["function"], dict):
                return t["function"].get("name") or str(id(t))
            if "name" in t:
                return t.get("name") or str(id(t))
    except Exception:
        pass
    return str(id(t))


def _shorten_for_log(text: Optional[str], limit: int = 400) -> str:
    """Collapse whitespace and cap length for log safety."""
    if not text:
        return ""
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    overflow = len(compact) - limit
    return f"{compact[:limit]}…(+{overflow} chars)"


def _merge_tool_schemas(server_schemas: List[Any], client_schemas: Optional[List[Any]]) -> List[Any]:
    """
    서버에서 로드한 도구 스키마 + 클라이언트 도구 스키마 병합(중복 제거)
    """
    client_schemas = client_schemas or []
    merged: Dict[str, Any] = {}
    for t in server_schemas + client_schemas:
        merged[_tool_key_for_merge(t)] = t
    return list(merged.values())


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    if isinstance(value, (int, float)):
        return value != 0
    return False


def _tool_input_dict(tool_input: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if isinstance(tool_input, dict):
        return tool_input
    return {}


def _should_route_to_guide(req: OpenAIChatRequest) -> bool:
    context = (req.context or "").lower()
    if context == "guide":
        return True

    tool_input = _tool_input_dict(req.tool_input)
    guide_flags = (
        tool_input.get("guide_mode"),
        tool_input.get("guide_agent"),
            tool_input.get("run_guide"),
    )
    return any(_parse_bool(flag) for flag in guide_flags if flag is not None)


def _format_tool_execution_message(tool_name: str, result: Any) -> str:
    try:
        rendered = json.dumps(result, ensure_ascii=False, indent=2)
    except Exception:
        rendered = str(result)
    message = [
        f"도구 `{tool_name}` 실행을 완료했습니다.",
        "",
        "실행 결과:",
        "```",
        rendered,
        "```",
        "",
        "다른 도움이 필요하시면 이어서 요청해주세요.",
    ]
    return "\n".join(message)

async def _get_or_create_session_and_history(
    req: OpenAIChatRequest, chat_service: ChatService, request: Request
):

    session = chat_service.get_or_create_session(
        session_id=req.session_id,
        user_agent=request.headers.get("User-Agent"),
        ip_address=request.client.host if request.client else None,
    )
    current_session_id = session["session_id"]

    raw_history = chat_service.get_chat_history(current_session_id, limit=20)
    history_dicts: List[Dict[str, Any]] = []
    if not req.messages:
        history_dicts.append({"role": "system", "content": "You are a helpful assistant."})

    current_user_content = ""
    for msg in raw_history:
        history_dicts.append({"role": msg.role, "content": msg.content})

    for msg in req.messages:
        message_dump = msg.model_dump(exclude_none=True)
        history_dicts.append(message_dump)
        if msg.role == "user":
            current_user_content = msg.content

    return session, current_session_id, history_dicts, current_user_content


async def _log_and_save_messages(
    chat_service: ChatService,
    current_session_id: str,
    current_user_content: str,
    final_message_content: str,
    session: dict,
    start_time: float,
    req: OpenAIChatRequest,
    response_status: int,
    error_message: str = None,
    *,
    selected_tool: Optional[str] = None,
    tool_execution_time_ms: Optional[int] = None,
    tool_success: Optional[bool] = None,
    tool_metadata: Optional[Dict[str, Any]] = None,
):
    turn = session["conversation_turns"] + 1
    chat_service.save_chat_message(
        session_id=current_session_id, role="user", content=current_user_content, turn_number=turn
    )
    chat_service.save_chat_message(
        session_id=current_session_id,
        role="assistant",
        content=final_message_content,
        turn_number=turn,
        selected_tool=selected_tool,
        tool_execution_time_ms=tool_execution_time_ms,
        tool_success=tool_success,
        tool_metadata=tool_metadata,
    )
    chat_service.update_session_turns(current_session_id)

    response_time_ms = int((time.time() - start_time) * 1000)
    chat_service.log_api_call(
        session_id=current_session_id,
        endpoint="/v1/chat/completions",
        method="POST",
        request_data={
            "model": req.model,
            "message_count": len(req.messages),
            "context": req.context,
        },
        response_status=response_status,
        response_time_ms=response_time_ms,
        error_message=error_message,
        selected_tool=selected_tool,
        tool_execution_time_ms=tool_execution_time_ms,
        tool_success=tool_success,
        tool_error_message=error_message,
    )


async def _handle_guide_agent_flow(
    *,
    req: OpenAIChatRequest,
    chat_service: ChatService,
    session: dict,
    current_session_id: str,
    masked_user_content: str,
    current_user_content: str,
    history_dicts: List[Dict[str, Any]],
    start_time: float,
    request: Request,
) -> Dict[str, Any]:
    base_url = os.getenv("GUIDE_AGENT_RAG_URL") or os.getenv("RAG_BASE_URL") or "http://coe-ragpipeline-dev:8001"

    tool_input = _tool_input_dict(req.tool_input)
    confirm = _parse_bool(tool_input.get("guide_confirm"))
    cancel = _parse_bool(tool_input.get("guide_cancel"))

    context = req.context or ""
    group_name = req.group_name

    try:
        server_schemas, server_functions = tool_dispatcher.get_available_tools_for_context(
            context,
            group_name,
        )
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("Guide flow failed to load server tools: %s", e)
        server_schemas, server_functions = [], {}

    pending_action = session.get("pending_tool_action")

    if cancel:
        if pending_action:
            session = chat_service.clear_pending_tool_action(current_session_id) or session
            pending_action = None
            final_message_content = "대기 중이던 도구 실행 요청을 취소했습니다."
        else:
            final_message_content = "취소할 대기 중인 도구 실행이 없습니다."

        final_message_dict = {"role": "assistant", "content": final_message_content}
        history_dicts.append(final_message_dict)
        await _log_and_save_messages(
            chat_service,
            current_session_id,
            masked_user_content,
            final_message_content,
            session,
            start_time,
            req,
            200,
        )

        return {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": req.model,
            "choices": [{"index": 0, "message": final_message_dict, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "session_id": current_session_id,
        }

    if confirm:
        if not pending_action:
            final_message_content = "실행할 대기 중인 도구가 없습니다. 먼저 제안된 도구를 확인한 뒤 다시 요청해주세요."
            final_message_dict = {"role": "assistant", "content": final_message_content}
            history_dicts.append(final_message_dict)
            await _log_and_save_messages(
                chat_service,
                current_session_id,
                masked_user_content,
                final_message_content,
                session,
                start_time,
                req,
                200,
            )
            return {
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": req.model,
                "choices": [{"index": 0, "message": final_message_dict, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "session_id": current_session_id,
            }

        tool_name = pending_action.get("tool_name") if isinstance(pending_action, dict) else None
        if not tool_name:
            session = chat_service.clear_pending_tool_action(current_session_id) or session
            final_message_content = "대기 중인 도구 정보가 잘못되어 실행을 건너뜁니다. 다시 요청해주세요."
            final_message_dict = {"role": "assistant", "content": final_message_content}
            history_dicts.append(final_message_dict)
            await _log_and_save_messages(
                chat_service,
                current_session_id,
                masked_user_content,
                final_message_content,
                session,
                start_time,
                req,
                200,
            )
            return {
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": req.model,
                "choices": [{"index": 0, "message": final_message_dict, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "session_id": current_session_id,
            }

        tool_fn = server_functions.get(tool_name)
        if not tool_fn:
            session = chat_service.clear_pending_tool_action(current_session_id) or session
            final_message_content = f"`{tool_name}` 도구를 현재 컨텍스트에서 찾을 수 없어 실행하지 못했습니다."
            final_message_dict = {"role": "assistant", "content": final_message_content}
            history_dicts.append(final_message_dict)
            await _log_and_save_messages(
                chat_service,
                current_session_id,
                masked_user_content,
                final_message_content,
                session,
                start_time,
                req,
                200,
            )
            return {
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": req.model,
                "choices": [{"index": 0, "message": final_message_dict, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "session_id": current_session_id,
            }

        tool_arguments = pending_action.get("arguments") if isinstance(pending_action, dict) else {}
        if not isinstance(tool_arguments, dict):
            tool_arguments = {}
        override_args = tool_input.get("guide_tool_args") or tool_input.get("tool_arguments")
        if isinstance(override_args, dict):
            tool_arguments.update(override_args)

        agent_state: AgentState = AgentState(
            history=history_dicts,
            input=current_user_content,
            mode="guide",
            scratchpad={},
            session_id=current_session_id,
            model_id=req.model,
            group_name=req.group_name,
            tool_input=tool_arguments,
            context=req.context,
            tools=server_schemas,
            requested_tool_choice=None,
        )

        start_exec = time.time()
        tool_success = False
        tool_result: Any = {}
        error_message = None

        try:
            tool_result = await tool_fn(tool_input=tool_arguments, state=agent_state)
            tool_success = True
        except Exception as exc:  # pragma: no cover - tool execution failure
            logger.exception("Guide tool execution failed: %s", exc)
            error_message = str(exc)
        exec_time_ms = int((time.time() - start_exec) * 1000)

        session = chat_service.clear_pending_tool_action(current_session_id) or session

        tool_output_content = json.dumps(tool_result, ensure_ascii=False, indent=2) if tool_success else (error_message or "도구 실행 중 오류가 발생했습니다.")
        history_dicts.append(
            {
                "role": "tool",
                "name": tool_name,
                "content": tool_output_content,
            }
        )

        if tool_success:
            final_message_content = _format_tool_execution_message(tool_name, tool_result)
        else:
            final_message_content = f"`{tool_name}` 실행 중 오류가 발생했습니다: {error_message or '알 수 없는 오류'}"

        final_message_dict = {"role": "assistant", "content": final_message_content}
        history_dicts.append(final_message_dict)

        await _log_and_save_messages(
            chat_service,
            current_session_id,
            masked_user_content,
            final_message_content,
            session,
            start_time,
            req,
            200 if tool_success else 500,
            error_message=None if tool_success else error_message,
            selected_tool=tool_name,
            tool_execution_time_ms=exec_time_ms,
            tool_success=tool_success,
            tool_metadata={"arguments": tool_arguments, "result": tool_result}
            if tool_success
            else {"arguments": tool_arguments, "error": error_message},
        )

        return {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": req.model,
            "choices": [{"index": 0, "message": final_message_dict, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "session_id": current_session_id,
        }

    paths: tuple[str, ...] = ()
    language = tool_input.get("language")
    raw_paths = tool_input.get("paths")
    if isinstance(raw_paths, list):
        paths = tuple(str(p) for p in raw_paths[:10])
    elif isinstance(raw_paths, str):
        paths = tuple(part.strip() for part in raw_paths.split(","))

    profile = tool_input.get("profile")
    profile = profile or req.group_name or "default"
    language = language or tool_input.get("locale")
    language = (language or "ko").lower()

    metadata: Dict[str, Any] = {
        "context": req.context,
        "group_name": req.group_name,
        "request_headers": {"User-Agent": request.headers.get("User-Agent")},
    }

    async with RagClient(base_url) as rag_client:
        guide_agent = GuideAgent(rag_client=rag_client)
        result = await guide_agent.run(
            prompt=current_user_content,
            profile=str(profile),
            language=language,
            paths=paths,
            metadata=metadata,
        )

    final_message_content = format_result_as_markdown(result)
    suggestion = None
    try:
        agent_state_for_suggestion: AgentState = AgentState(
            history=history_dicts,
            input=current_user_content,
            mode="guide",
            scratchpad={},
            session_id=current_session_id,
            model_id=req.model,
            group_name=req.group_name,
            tool_input=tool_input,
            context=req.context,
            tools=server_schemas,
            requested_tool_choice=None,
        )
        suggestion = await tool_dispatcher.maybe_execute_best_tool(
            current_user_content,
            req.context,
            agent_state_for_suggestion,
        )
    except Exception as exc:  # pragma: no cover - auto routing failure
        logger.info("Guide auto-route suggestion failed: %s", exc)

    if suggestion:
        tool_name = suggestion.get("tool_name")
        if tool_name and tool_name in server_functions:
            action_payload = {
                "tool_name": tool_name,
                "tool_type": suggestion.get("tool_type"),
                "arguments": suggestion.get("arguments") or {},
                "source": suggestion.get("source"),
            }
            session = chat_service.set_pending_tool_action(current_session_id, action_payload) or session

            suggestion_lines = ["", "**권장 도구 실행 안내**"]
            if suggestion.get("tool_type") == "flow":
                flow_name = suggestion.get("flow_name") or action_payload["arguments"].get("flow_name")
                suggestion_lines.append(f"- LangFlow: `{flow_name or tool_name}`")
            else:
                suggestion_lines.append(f"- 제안 도구: `{tool_name}`")
            if suggestion.get("reason"):
                suggestion_lines.append(f"- 선택 이유: {suggestion['reason']}")
            suggestion_lines.extend(
                [
                    "- 실행하려면 `tool_input.guide_confirm=true` 를 포함해 다시 요청해주세요.",
                    "- 취소하려면 `tool_input.guide_cancel=true` 를 전달하면 됩니다.",
                ]
            )
            final_message_content += "\n\n" + "\n".join(suggestion_lines)
        else:
            if pending_action:
                session = chat_service.clear_pending_tool_action(current_session_id) or session
                pending_action = None
    else:
        if pending_action:
            session = chat_service.clear_pending_tool_action(current_session_id) or session
            pending_action = None

    final_message_dict = {"role": "assistant", "content": final_message_content}
    history_dicts.append(final_message_dict)

    await _log_and_save_messages(
        chat_service,
        current_session_id,
        masked_user_content,
        final_message_content,
        session,
        start_time,
        req,
        200,
    )

    return {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [{"index": 0, "message": final_message_dict, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "session_id": current_session_id,
    }


# -----------------------------
# LangGraph Agent 요청 처리
# -----------------------------
async def handle_agent_request(
    req: OpenAIChatRequest,
    agent,
    agent_model_id: str,
    request: Request,
    db: Session,
):
    logger.debug("Entering handle_agent_request function.")
    """
    LangGraph 에이전트 요청 처리
    - context(UI 구분자)에 맞춰 서버 도구 세트 로드(get_available_tools_for_context)
    - 클라이언트 제공 tools와 병합하여 Agent에 전달
    """
    start_time = time.time()
    chat_service = get_chat_service(db)

    session, current_session_id, history_dicts, current_user_content = await _get_or_create_session_and_history(
        req, chat_service, request
    )

    masked_user_content, pii_hits = scrub_text(current_user_content)
    if pii_hits:
        logger.info(
            "[PII] session=%s masked_types=%s",
            current_session_id,
            ",".join(sorted({hit["type"] for hit in pii_hits})),
        )

    logger.info(
        "[CHAT][REQUEST] session=%s context=%s group=%s model=%s user=%s",
        current_session_id,
        req.context or "",
        req.group_name or "",
        req.model,
        _shorten_for_log(masked_user_content),
    )

    if _should_route_to_guide(req):
        logger.info(
            "[GUIDE] Routing to guide agent | session=%s group=%s",
            current_session_id,
            req.group_name or "",
        )
        return await _handle_guide_agent_flow(
            req=req,
            chat_service=chat_service,
            session=session,
            current_session_id=current_session_id,
            masked_user_content=masked_user_content,
            current_user_content=current_user_content,
            history_dicts=history_dicts,
            start_time=start_time,
            request=request,
        )

    if pii_hits:
        final_message_content = PII_BLOCK_MESSAGE
        final_message_dict = {"role": "assistant", "content": final_message_content}
        await _log_and_save_messages(
            chat_service,
            current_session_id,
            masked_user_content,
            final_message_content,
            session,
            start_time,
            req,
            200,
        )
        if req.stream:
            return StreamingResponse(
                agent_stream_generator(req.model, final_message_dict, current_session_id),
                media_type="text/event-stream",
            )
        return {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": req.model,
            "choices": [{"index": 0, "message": final_message_dict, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "session_id": current_session_id,
        }

    # 1) context 기반 서버 도구 스키마 로드
    server_schemas: List[Any] = []
    try:
        from services import tool_dispatcher  # 프로젝트의 dispatcher

        if hasattr(tool_dispatcher, "get_available_tools_for_context"):
            # (schemas, functions) 튜플을 반환하므로 schemas만 사용
            server_schemas, _functions = tool_dispatcher.get_available_tools_for_context(
                req.context or "",
                req.group_name,
            )
            logger.info(
                f"[TOOLS] context='{req.context}' → server_schemas={len(server_schemas)}"
            )
        else:
            logger.info("tool_dispatcher.get_available_tools_for_context 가 없어 서버 도구 로딩을 생략합니다.")
    except Exception as e:
        logger.warning(f"서버 도구 로딩 실패(context='{req.context}'): {e}")

    # 2) 클라이언트 도구와 병합
    resolved_tools = _merge_tool_schemas(server_schemas, req.tools)

    agent_state = AgentState(
        history=history_dicts,
        input=current_user_content,
        mode="coding",  # 현재는 고정
        scratchpad={},
        session_id=current_session_id,
        model_id=req.model,
        group_name=req.group_name,
        tool_input=req.tool_input,
        context=req.context, # UI 컨텍스트: 에이전트 내부 분기/로깅에 활용
        tools=resolved_tools,
        requested_tool_choice=req.tool_choice,
    )

    try:
        # --- Fallback to agent flow (tool dispatcher handles auto-routing) ---
        logger.info(
            "Invoking agent | model='%s' context='%s' history=%d tools=%d",
            agent_state["model_id"],
            agent_state.get("context"),
            len(agent_state["history"]),
            len(agent_state.get("tools") or []),
        )
        result_state = await agent.ainvoke(agent_state)
        logger.info("Agent invocation successful.")

        final_message_dict = result_state["history"][-1]
        final_message_content = final_message_dict.get("content") or ""

        await _log_and_save_messages(
            chat_service,
            current_session_id,
            masked_user_content,
            final_message_content,
            session,
            start_time,
            req,
            200,
        )

        if req.stream:
            return StreamingResponse(
                agent_stream_generator(req.model, final_message_dict, current_session_id),
                media_type="text/event-stream",
            )
        else:
            return {
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": req.model,
                "choices": [{"index": 0, "message": final_message_dict, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "session_id": current_session_id,
            }

    except Exception as e:
        error_message = str(e)
        logger.error("에이전트 실행 중 예외 발생: %s: %s", type(e).__name__, error_message, exc_info=True)

        await _log_and_save_messages(
            chat_service, current_session_id, masked_user_content, "", session, start_time, req, 500, error_message
        )

        raise HTTPException(status_code=500, detail=f"에이전트 실행 오류: {error_message}")


# -----------------------------
# 일반 LLM 프록시
# -----------------------------
async def handle_llm_proxy_request(req: OpenAIChatRequest):
    """
    일반 LLM 모델 요청 프록시
    - tools/tool_choice None 제거
    - tool_choice만 있고 tools 없는 경우 제거(또는 무시)
    - 일부 OpenAI 호환 게이트웨이의 엄격 검증으로 인한 400 방지
    """
    try:
        model_info = get_model_info(req.model)
        if not model_info:
            raise HTTPException(
                status_code=400,
                detail=f"지원하지 않는 모델입니다: {req.model}. 지원 모델 목록은 /v1/models 엔드포인트에서 확인하세요.",
            )

        model_client = get_client_for_model(req.model)

        last_user_message = ""
        for msg in reversed(req.messages or []):
            if msg.role == "user":
                last_user_message = msg.content
                break
        logger.info(
            "[CHAT][LLM REQUEST] model=%s user=%s",
            req.model,
            _shorten_for_log(last_user_message),
        )

        params: Dict[str, Any] = {
            "model": req.model,
            "messages": [msg.model_dump(exclude_none=True) for msg in req.messages],
            "stream": req.stream,
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        }

        # tools / tool_choice 설정 (None 금지)
        if req.tools:
            params["tools"] = [t.model_dump(exclude_none=True) for t in req.tools]

        if req.tool_choice is not None:
            if "tools" in params:
                params["tool_choice"] = req.tool_choice
            else:
                logger.warning("tool_choice provided without tools → drop tool_choice")

        # 최종 None 제거
        params = _drop_none_fields(params)

        logger.debug(f"[LLM Proxy] effective params keys: {list(params.keys())}")

        response = model_client.chat.completions.create(**params)

        if req.stream:
            return StreamingResponse(
                proxy_stream_generator(response),
                media_type="text/event-stream",
            )
        else:
            return response.model_dump(exclude_none=True)

    except HTTPException:
        raise
    except Exception as e:
        # OpenAI SDK BadRequest를 400으로 패스스루 (가능한 경우)
        if OPENAI_IMPORTED and isinstance(e, getattr(openai, "BadRequestError", Exception)):
            detail = str(e)
            try:
                detail = getattr(e, "response", None) or getattr(e, "body", None) or detail
            except Exception:
                pass
            raise HTTPException(status_code=400, detail=f"Upstream 400: {detail}")

        logger.error("LLM API 호출 오류: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"LLM API 호출 오류: {str(e)}")


# -----------------------------
# (옵션) RAG 연계
# -----------------------------
import os as _os
_RAG_BASE = _os.getenv("RAG_PIPELINE_URL", "http://ragpipeline:8001")
RAG_SERVICE_URL = f"{_RAG_BASE}/api/v1/search"
RAG_SCORE_THRESHOLD = 0.7


async def handle_rag_request(req: OpenAIChatRequest, request: Request, db: Session, agent_info: dict):
    """
    group_name이 있는 경우 RAG 요청 처리
    """
    start_time = time.time()
    chat_service = get_chat_service(db)

    session, current_session_id, history_dicts, current_user_content = await _get_or_create_session_and_history(
        req, chat_service, request
    )

    masked_user_content, rag_pii_hits = scrub_text(current_user_content)
    if rag_pii_hits:
        logger.info(
            "[PII] session=%s masked_types=%s",
            current_session_id,
            ",".join(sorted({hit["type"] for hit in rag_pii_hits})),
        )

    logger.info(
        "[CHAT][RAG REQUEST] session=%s context=%s group=%s model=%s user=%s",
        current_session_id,
        req.context or "",
        req.group_name or "",
        req.model,
        _shorten_for_log(masked_user_content),
    )

    if rag_pii_hits:
        final_message_content = PII_BLOCK_MESSAGE
        final_message_dict = {"role": "assistant", "content": final_message_content}
        await _log_and_save_messages(
            chat_service,
            current_session_id,
            masked_user_content,
            final_message_content,
            session,
            start_time,
            req,
            200,
        )
        if req.stream:
            return StreamingResponse(
                agent_stream_generator(req.model, final_message_dict, current_session_id),
                media_type="text/event-stream",
            )
        return {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": req.model,
            "choices": [{"index": 0, "message": final_message_dict, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "session_id": current_session_id,
        }

    user_query = current_user_content
    retrieved_documents: List[Dict[str, Any]] = []

    try:
        async with httpx.AsyncClient() as client:
            rag_request_payload = {"query": user_query, "k": 10, "group_name": req.group_name}
            logger.info(f"Calling RAG service at {RAG_SERVICE_URL} with payload: {rag_request_payload}")
            response = await client.post(RAG_SERVICE_URL, json=rag_request_payload, timeout=300.0)
            response.raise_for_status()
            retrieved_documents = response.json()
            logger.info(f"Received {len(retrieved_documents)} documents from RAG service.")
    except httpx.RequestError as e:
        error_message = f"RAG 서비스 호출 실패: {e}"
        logger.error(error_message, exc_info=True)
        await _log_and_save_messages(
            chat_service, current_session_id, masked_user_content, "", session, start_time, req, 500, error_message
        )
        raise HTTPException(status_code=500, detail=error_message)
    except httpx.HTTPStatusError as e:
        error_message = f"RAG 서비스 응답 오류: {e.response.status_code} - {e.response.text}"
        logger.error(error_message, exc_info=True)
        await _log_and_save_messages(
            chat_service, current_session_id, masked_user_content, "", session, start_time, req, 500, error_message
        )
        raise HTTPException(status_code=500, detail=error_message)
    except Exception as e:
        error_message = f"RAG 처리 중 알 수 없는 오류 발생: {e}"
        logger.error(error_message, exc_info=True)
        await _log_and_save_messages(
            chat_service, current_session_id, masked_user_content, "", session, start_time, req, 500, error_message
        )
        raise HTTPException(status_code=500, detail=error_message)

    satisfactory_documents = [doc for doc in retrieved_documents if doc.get("rerank_score", 0) >= RAG_SCORE_THRESHOLD]

    if not satisfactory_documents:
        logger.warning(
            f"No satisfactory documents retrieved from RAG for query: {user_query}. Falling back to agent/LLM proxy logic."
        )
        agent = agent_info["agent"]
        if req.model == agent_info["model_id"]:
            return await handle_agent_request(req, agent, req.model, request, db)
        else:
            return await handle_llm_proxy_request(req)

    context = "\n\n".join([doc["content"] for doc in satisfactory_documents])

    messages_for_llm = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant. Use the following context to answer the user's question. "
                "If the context does not provide enough information, state that you cannot answer based on the provided context.\n\n"
                f"Context:\n{context}"
            ),
        },
        {"role": "user", "content": user_query},
    ]

    try:
        model_client = get_client_for_model(req.model)
        llm_params: Dict[str, Any] = {
            "model": req.model,
            "messages": messages_for_llm,
            "stream": req.stream,
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        }
        llm_params = _drop_none_fields(llm_params)

        llm_response = model_client.chat.completions.create(**llm_params)

        if req.stream:
            return StreamingResponse(proxy_stream_generator(llm_response), media_type="text/event-stream")
        else:
            final_message_dict = llm_response.model_dump(exclude_none=True)["choices"][0]["message"]
            final_message_content = final_message_dict.get("content", "")

            await _log_and_save_messages(
                chat_service,
                current_session_id,
                masked_user_content,
                final_message_content,
                session,
                start_time,
                req,
                200,
            )

            return {
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": req.model,
                "choices": [{"index": 0, "message": final_message_dict, "finish_reason": "stop"}],
                "usage": llm_response.usage.model_dump()
                if getattr(llm_response, "usage", None)
                else {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "session_id": current_session_id,
            }

    except Exception as e:
        error_message = str(e)
        logger.error("RAG LLM 호출 오류: %s: %s", type(e).__name__, error_message, exc_info=True)

        await _log_and_save_messages(
            chat_service, current_session_id, masked_user_content, "", session, start_time, req, 500, error_message
        )

        raise HTTPException(status_code=500, detail=f"RAG LLM 호출 오류: {error_message}")


# -----------------------------
# 엔드포인트
# -----------------------------
@router.post("/chat/completions")
@router.post("/completions")
async def chat_completions(
    req: OpenAIChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    agent_info: dict = Depends(get_agent_info),
):
    """
    기본적으로 LangGraph Agent로 처리
    (원하면 조건부로 RAG/LLM 프록시 분기 추가 가능)
    """
    agent = agent_info["agent"]
    return await handle_agent_request(req, agent, req.model, request, db)
