"""
채팅 관련 API 엔드포인트들을 담당하는 모듈입니다.
"""

import time
import uuid
import logging
import json

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.schemas import (
    OpenAIChatRequest
)
from core.database import get_db
from services.chat_service import get_chat_service, ChatService
from utils.streaming_utils import agent_stream_generator

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["🤖 AI Chat"],
    prefix="/v1",
)



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

@router.post("/chat/completions")
@router.post("/completions")
async def chat_completions(
    req: OpenAIChatRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """AI 에이전트 또는 일반 LLM 프록시를 통해 채팅 응답을 처리합니다."""
    
    start_time = time.time()
    chat_service = get_chat_service(db)

    session, current_session_id, history_dicts, current_user_content = await _get_or_create_session_and_history(
        req, chat_service, request
    )

    try:
        # Call the new process_chat_request method in ChatService
        # Use the last user message from req.messages as the current user_message
        last_user_message = ""
        if req.messages:
            for msg in reversed(req.messages):
                if msg.role == "user":
                    last_user_message = msg.content
                    break
        
        # Default context for now, can be made dynamic later if needed
        context = req.context if req.context is not None else "default" 

        llm_response = await chat_service.process_chat_request(
            session_id=current_session_id,
            user_message=last_user_message,
            model_id=req.model,
            context=context
        )

        if "tool_call_response" in llm_response:
            # LLM returned a tool call, pass it directly to the client
            tool_call_data = llm_response["tool_call_response"]
            logger.info(f"LLM requested tool call: {tool_call_data.get('tool_calls')}")
            
            # Log and save messages for the user's input and the assistant's tool call
            # The tool_call_data already contains the assistant's message with tool_calls
            # We need to ensure the user's message is saved, which is done inside process_chat_request
            # The assistant's tool call message is also saved inside process_chat_request
            
            # Format into OpenAI-compatible response
            response_to_continue = {
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": req.model,
                "choices": [{
                    "index": 0,
                    "message": tool_call_data,
                    "finish_reason": "tool_calls" # Use tool_calls as finish reason
                }],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, # Usage not tracked here
                "session_id": current_session_id
            }
            logger.debug(f"Sending raw JSON to Continue: {json.dumps(response_to_continue, indent=2)}")
            return response_to_continue
        elif "text_response" in llm_response:
            # LLM returned a text response
            final_message_content = llm_response["text_response"]
            
            # Log and save messages (user's message saved in process_chat_request, assistant's text response also saved there)
            # Only need to log the API call here
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
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": final_message_content}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, # Usage not tracked here
                    "session_id": current_session_id
                }
        elif "error" in llm_response:
            error_message = llm_response["error"]
            logger.error(f"LLM 처리 중 오류 발생: {error_message}")
            await _log_and_save_messages(
                chat_service, current_session_id, current_user_content,
                "", session, start_time, req, 500, error_message
            )
            raise HTTPException(status_code=500, detail=f"LLM 처리 오류: {error_message}")

    except Exception as e:
        error_message = str(e)
        logger.error(f"채팅 요청 처리 중 예외 발생: {type(e).__name__}: {error_message}", exc_info=True)
        
        await _log_and_save_messages(
            chat_service, current_session_id, current_user_content,
            "", session, start_time, req, 500, error_message
        )
        
        raise HTTPException(status_code=500, detail=f"채팅 요청 처리 오류: {error_message}")
