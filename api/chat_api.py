"""
채팅 관련 API 엔드포인트들을 담당하는 모듈입니다.

리팩토링 핵심
- context(프론트 UI 구분자)에 맞춰 서버 도구 세트를 로드(get_available_tools_for_context)
- 클라이언트 제공 tools와 병합 후 LangGraph Agent에 전달
- LLM 프록시 호출 시 tools/tool_choice의 None 제거 및 교차 검증 (타사 OpenAI 호환 게이트웨이 400 방지)
- BadRequest는 가능하면 400으로 패스스루, 기타 예외는 500
"""

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
from utils.streaming_utils import agent_stream_generator, proxy_stream_generator

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
):
    turn = session["conversation_turns"] + 1
    chat_service.save_chat_message(
        session_id=current_session_id, role="user", content=current_user_content, turn_number=turn
    )
    chat_service.save_chat_message(
        session_id=current_session_id, role="assistant", content=final_message_content, turn_number=turn
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
    )


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

    logger.info(
        "[CHAT][REQUEST] session=%s context=%s group=%s model=%s user=%s",
        current_session_id,
        req.context or "",
        req.group_name or "",
        req.model,
        _shorten_for_log(masked_user_content),
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
