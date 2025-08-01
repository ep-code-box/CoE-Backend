"""
채팅 관련 API 엔드포인트들을 담당하는 모듈입니다.
"""

import time
import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from core.schemas import ChatRequest, ChatResponse, OpenAIChatRequest
from core.llm_client import client
from utils.streaming_utils import agent_stream_generator, proxy_stream_generator
from tools.utils import find_last_user_message

# 전역 변수로 에이전트 정보 저장
_agent = None
_agent_model_id = None

router = APIRouter()


async def handle_agent_request(req: OpenAIChatRequest, agent, agent_model_id: str):
    """
    CoE 에이전트 요청을 처리합니다.
    
    Args:
        req: OpenAI 호환 채팅 요청
        agent: 컴파일된 LangGraph 에이전트
        agent_model_id: 에이전트 모델 ID
        
    Returns:
        스트리밍 또는 일반 JSON 응답
    """
    state = {"messages": [msg.model_dump() for msg in req.messages]}
    
    # 에이전트 실행
    result = await agent.ainvoke(state)
    final_message = find_last_user_message(result["messages"], role="assistant")

    if req.stream:
        # 스트리밍 응답
        return StreamingResponse(
            agent_stream_generator(req.model, final_message),
            media_type="text/event-stream"
        )
    else:
        # 일반 JSON 응답
        return {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": req.model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": final_message}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}  # 사용량은 추적하지 않음
        }


async def handle_llm_proxy_request(req: OpenAIChatRequest):
    """
    일반 LLM 모델 요청을 프록시합니다.
    
    Args:
        req: OpenAI 호환 채팅 요청
        
    Returns:
        프록시된 LLM 응답
    """
    try:
        # OpenAI 클라이언트로 요청을 그대로 전달
        response = client.chat.completions.create(
            model=req.model,
            messages=[msg.model_dump() for msg in req.messages],
            stream=req.stream,
            temperature=req.temperature,
            max_tokens=req.max_tokens
        )
        
        if req.stream:
            # 스트리밍 응답 프록시
            return StreamingResponse(
                proxy_stream_generator(response), 
                media_type="text/event-stream"
            )
        else:
            # 일반 JSON 응답 프록시
            return response.model_dump()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM API 호출 오류: {str(e)}")


def set_agent_info(agent, agent_model_id: str):
    """
    에이전트 정보를 전역 변수에 설정합니다.
    
    Args:
        agent: 컴파일된 LangGraph 에이전트
        agent_model_id: 에이전트 모델 ID
    """
    global _agent, _agent_model_id
    _agent = agent
    _agent_model_id = agent_model_id


@router.post("/v1/chat/completions")
async def chat_completions(req: OpenAIChatRequest):
    """
    OpenAI API와 호환되는 채팅 엔드포인트입니다.
    요청된 모델 ID에 따라 CoE 에이전트를 실행하거나, 일반 LLM 호출을 프록시합니다.
    """
    print(f"DEBUG: Received request: {req}")
    print(f"DEBUG: Agent model ID: {_agent_model_id}")
    
    # 1. CoE 에이전트 모델을 요청한 경우
    if req.model == _agent_model_id:
        return await handle_agent_request(req, _agent, _agent_model_id)
    # 2. 일반 LLM 모델을 요청한 경우 (프록시 역할)
    else:
        return await handle_llm_proxy_request(req)


@router.post("/chat", response_model=ChatResponse, deprecated=True, summary="[Deprecated] Use /v1/chat/completions instead")
async def legacy_chat_endpoint(req: ChatRequest):
    """이 엔드포인트는 더 이상 사용되지 않습니다. /v1/chat/completions를 사용하세요."""
    state = {"messages": [msg.model_dump() for msg in req.messages]}
    result = await _agent.ainvoke(state)
    return ChatResponse(messages=result["messages"])


def create_chat_router(agent, agent_model_id: str):
    """
    채팅 라우터를 생성합니다. 에이전트와 모델 ID를 주입받습니다.
    
    Args:
        agent: 컴파일된 LangGraph 에이전트
        agent_model_id: 에이전트 모델 ID
        
    Returns:
        APIRouter: 설정된 채팅 라우터
    """
    set_agent_info(agent, agent_model_id)
    return router