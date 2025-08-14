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
    OpenAIChatRequest, AiderChatRequest, AgentState
)
from core.llm_client import get_client_for_model, get_model_info
from core.database import get_db
from services.chat_service import get_chat_service, ChatService
from utils.streaming_utils import agent_stream_generator, proxy_stream_generator

logger = logging.getLogger(__name__)

# 전역 변수로 에이전트 정보 저장
_agent = None
_agent_model_id = None
_aider_agent = None
_aider_agent_model_id = None

router = APIRouter(
    tags=["🤖 AI Chat"],
    prefix="/v1",
)

def set_agent_info(agent, agent_model_id: str):
    global _agent, _agent_model_id
    _agent = agent
    _agent_model_id = agent_model_id

def set_aider_agent_info(agent, agent_model_id: str):
    global _aider_agent, _aider_agent_model_id
    _aider_agent = agent
    _aider_agent_model_id = agent_model_id

async def handle_agent_request(req: OpenAIChatRequest, agent, agent_model_id: str, 
                              request: Request, db: Session):
    """
    새로운 Modal Context Protocol 에이전트 요청을 처리합니다.
    """
    start_time = time.time()
    chat_service = get_chat_service(db)

    # 1. 세션 가져오기 또는 생성
    session = chat_service.get_or_create_session(
        session_id=req.session_id,
        user_agent=request.headers.get("User-Agent"),
        ip_address=request.client.host if request.client else None
    )
    current_session_id = session['session_id']

    # 2. 대화 기록을 가져오고 현재 사용자 메시지를 추가합니다.
    raw_history = chat_service.get_chat_history(current_session_id, limit=20)
    history_dicts = []
    if not raw_history and not req.messages:
         # 시스템 프롬프트가 여기에 추가될 수 있습니다.
        history_dicts.append({"role": "system", "content": "You are a helpful assistant."})

    for msg in raw_history:
        history_dicts.append({"role": msg.role, "content": msg.content})
    
    current_user_content = ""
    for msg in req.messages:
        message_dump = msg.model_dump(exclude_none=True)
        history_dicts.append(message_dump)
        if msg.role == 'user':
            current_user_content = msg.content

    # 3. 새로운 AgentState를 구성합니다.
    # TODO: 'mode'를 사용자 요청이나 세션 상태에 따라 동적으로 결정해야 합니다.
    agent_state = AgentState(
        history=history_dicts,
        input=current_user_content,
        mode="coding", # 현재는 'coding' 모드로 고정
        scratchpad={},
        session_id=current_session_id,
    )

    try:
        # 4. 새로운 에이전트를 호출합니다.
        logger.info(f"Invoking new agent with state: mode='{agent_state['mode']}', history_len={len(agent_state['history'])}")
        result_state = await agent.ainvoke(agent_state)
        logger.info("New agent invocation successful.")

        # 5. 결과에서 최종 응답을 추출합니다.
        final_message_dict = result_state["history"][-1]
        final_message_content = final_message_dict.get("content", "")

        # 6. DB에 메시지 저장 및 로깅
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
            response_status=200,
            response_time_ms=response_time_ms
        )

        # 7. 스트리밍 또는 일반 응답 반환
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
        response_time_ms = int((time.time() - start_time) * 1000)
        error_message = str(e)
        logger.error(f"에이전트 실행 중 예외 발생: {type(e).__name__}: {error_message}", exc_info=True)
        
        chat_service.log_api_call(
            session_id=current_session_id,
            endpoint="/v1/chat/completions",
            method="POST",
            request_data={"model": req.model, "message_count": len(req.messages)},
            response_status=500,
            response_time_ms=response_time_ms,
            error_message=error_message
        )
        
        raise HTTPException(status_code=500, detail=f"에이전트 실행 오류: {error_message}")

async def handle_llm_proxy_request(req: OpenAIChatRequest):
    """
    일반 LLM 모델 요청을 프록시합니다.
    """
    try:
        model_info = get_model_info(req.model)
        if not model_info:
            raise HTTPException(
                status_code=400, 
                detail=f"지원하지 않는 모델입니다: {req.model}. 지원 모델 목록은 /v1/models 엔드포인트에서 확인하세요."
            )
        
        model_client = get_client_for_model(req.model)
        
        params = {
            "model": req.model,
            "messages": [msg.model_dump(exclude_none=True) for msg in req.messages],
            "stream": req.stream,
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        }
        
        if req.tools:
            params["tools"] = [t.model_dump(exclude_none=True) for t in req.tools]
        if req.tool_choice:
            params["tool_choice"] = req.tool_choice

        response = model_client.chat.completions.create(**params)
        
        if req.stream:
            return StreamingResponse(
                proxy_stream_generator(response), 
                media_type="text/event-stream"
            )
        else:
            return response.model_dump(exclude_none=True)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"LLM API 호출 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"LLM API 호출 오류: {str(e)}")

@router.post("/chat/completions")
async def chat_completions(req: OpenAIChatRequest, request: Request, db: Session = Depends(get_db)):
    """AI 에이전트 또는 일반 LLM 프록시를 통해 채팅 응답을 처리합니다."""
    
    agent_model_ids = [_agent_model_id, _aider_agent_model_id]

    if req.model in agent_model_ids:
        # 요청된 모델이 등록된 에이전트 모델 중 하나인 경우
        agent_to_use = _agent if req.model == _agent_model_id else _aider_agent
        return await handle_agent_request(req, agent_to_use, req.model, request, db)
    else:
        # 등록된 에이전트 모델이 아니면 LLM 프록시로 처리
        return await handle_llm_proxy_request(req)
