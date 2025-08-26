"""
채팅 관련 API 엔드포인트들을 담당하는 모듈입니다.
"""

import time
import uuid
import logging

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.schemas import (
    OpenAIChatRequest, AgentState
)
from core.database import get_db
from services.chat_service import get_chat_service, ChatService
from utils.streaming_utils import agent_stream_generator

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["🤖 AI Chat"],
    prefix="/v1",
)

_agent_instance = None

def set_agent_info(agent, agent_model_id: str):
    global _agent_instance
    _agent_instance = {"agent": agent, "model_id": agent_model_id}

async def get_agent_info():
    if _agent_instance is None:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    return _agent_instance

async def _get_or_create_session_and_history(
    req: OpenAIChatRequest, chat_service: ChatService, request: Request
):
    session = chat_service.get_or_create_session(
        session_id=req.session_id,
        user_agent=request.headers.get("User-Agent"),
        ip_address=request.client.host if request.client else None
    )
    current_session_id = session['session_id']

    raw_history = chat_service.get_chat_history(current_session_id, limit=20)
    history_dicts = []
    if not req.messages:
        history_dicts.append({"role": "system", "content": "You are a helpful assistant."})

    for msg in raw_history:
        history_dicts.append({"role": msg.role, "content": msg.content})
    
    current_user_content = ""
    for msg in req.messages:
        message_dump = msg.model_dump(exclude_none=True)
        history_dicts.append(message_dump)
        if msg.role == 'user':
            current_user_content = msg.content
    
    return session, current_session_id, history_dicts, current_user_content

async def _log_and_save_messages(
    chat_service: ChatService, current_session_id: str, current_user_content: str,
    final_message_content: str, session: dict, start_time: float, req: OpenAIChatRequest,
    response_status: int, error_message: str = None
):
    chat_service.save_chat_message(
        session_id=current_session_id,
        role="user",
        content=current_user_content,
        turn_number=session['conversation_turns'] + 1
    )
    chat_service.save_chat_message(
        session_id=current_session_id,
        role="assistant",
        content=final_message_content,
        turn_number=session['conversation_turns'] + 1
    )
    chat_service.update_session_turns(current_session_id)
    
    response_time_ms = int((time.time() - start_time) * 1000)
    chat_service.log_api_call(
        session_id=current_session_id,
        endpoint="/v1/chat/completions",
        method="POST",
        request_data={"model": req.model, "message_count": len(req.messages)},
        response_status=response_status,
        response_time_ms=response_time_ms,
        error_message=error_message
    )

async def handle_agent_request(req: OpenAIChatRequest, agent, agent_model_id: str, 
                              request: Request, db: Session):
    """
    새로운 Modal Context Protocol 에이전트 요청을 처리합니다.
    """
    start_time = time.time()
    chat_service = get_chat_service(db)

    session, current_session_id, history_dicts, current_user_content = await _get_or_create_session_and_history(
        req, chat_service, request
    )

    agent_state = AgentState(
        history=history_dicts,
        input=current_user_content,
        mode="coding", # 현재는 'coding' 모드로 고정
        scratchpad={},
        session_id=current_session_id,
        model_id=req.model,
        group_name=req.group_name,
        context=req.context,
    )

    try:
        logger.info(f"Invoking new agent with state: mode='{agent_state['mode']}', history_len={len(agent_state['history'])} ")
        result_state = await agent.ainvoke(agent_state)
        logger.info("New agent invocation successful.")

        final_message_dict = result_state["history"][-1]
        final_message_content = final_message_dict.get("content", "")

        await _log_and_save_messages(
            chat_service, current_session_id, current_user_content,
            final_message_content, session, start_time, req, 200
        )
        
        if req.stream:
            return StreamingResponse(
                agent_stream_generator(req.model, final_message_content, current_session_id),
                media_type="text/event-stream"
            )
        else:
            return {
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": req.model,
                "choices": [{"index": 0, "message": final_message_dict, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "session_id": current_session_id
            }

    except Exception as e:
        error_message = str(e)
        logger.error(f"에이전트 실행 중 예외 발생: {type(e).__name__}: {error_message}", exc_info=True)
        
        await _log_and_save_messages(
            chat_service, current_session_id, current_user_content,
            "", session, start_time, req, 500, error_message
        )
        
        raise HTTPException(status_code=500, detail=f"에이전트 실행 오류: {error_message}")

@router.post("/chat/completions")
@router.post("/completions")
async def chat_completions(
    req: OpenAIChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    agent_info: dict = Depends(get_agent_info)
):
    """AI 에이전트 또는 일반 LLM 프록시를 통해 채팅 응답을 처리합니다."""
    
    agent = agent_info["agent"]
    
    # 모든 모델 요청을 에이전트에게 전달하여 도구 사용을 결정하도록 합니다.
    return await handle_agent_request(req, agent, req.model, request, db)
