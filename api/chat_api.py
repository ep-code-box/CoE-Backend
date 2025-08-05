"""
채팅 관련 API 엔드포인트들을 담당하는 모듈입니다.
"""

import time
import uuid
import logging
import time
import uuid
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.schemas import ChatRequest, ChatResponse, OpenAIChatRequest
from core.llm_client import client, get_client_for_model, get_model_info
from core.database import get_db
from services.chat_service import get_chat_service
from utils.streaming_utils import agent_stream_generator, proxy_stream_generator
from tools.utils import find_last_user_message

logger = logging.getLogger(__name__)

# 전역 변수로 에이전트 정보 저장
_agent = None
_agent_model_id = None

router = APIRouter(
    tags=["🤖 AI Chat"],
    prefix="/v1",
    responses={
        200: {"description": "채팅 응답 성공"},
        400: {"description": "잘못된 요청"},
        500: {"description": "서버 오류"}
    }
)


async def handle_agent_request(req: OpenAIChatRequest, agent, agent_model_id: str, 
                              request: Request, db: Session):
    """
    CoE 에이전트 요청을 처리합니다.
    
    Args:
        req: OpenAI 호환 채팅 요청
        agent: 컴파일된 LangGraph 에이전트
        agent_model_id: 에이전트 모델 ID
        request: FastAPI Request 객체
        db: 데이터베이스 세션
        
    Returns:
        스트리밍 또는 일반 JSON 응답
    """
    start_time = time.time()
    chat_service = get_chat_service(db) # Pass the db session here
    
    # 세션 ID 추출 (헤더에서 또는 새로 생성)
    session_id = request.headers.get("X-Session-ID")
    user_agent = request.headers.get("User-Agent")
    ip_address = request.client.host if request.client else None
    
    # 세션 생성 또는 조회
    session = chat_service.get_or_create_session(
        session_id=session_id,
        user_agent=user_agent,
        ip_address=ip_address
    )
    
    # 메시지 내용이 None인 경우 빈 문자열로 대체
    sanitized_messages = []
    for msg in req.messages:
        msg_dump = msg.model_dump()
        if msg_dump.get("content") is None:
            msg_dump["content"] = ""
        sanitized_messages.append(msg_dump)

    # 사용자 메시지 저장
    user_message = find_last_user_message(sanitized_messages)
    if user_message is not None:
        chat_service.save_chat_message(
            session_id=session['session_id'],
            role="user",
            content=user_message,
            turn_number=session['conversation_turns'] + 1
        )
    
    # 에이전트 상태 준비
    state = {"messages": sanitized_messages}
    
    # 도구 선택 및 실행 정보를 추적하기 위한 컨텍스트 설정
    tool_context = {
        "session_id": session['session_id'],
        "chat_service": chat_service,
        "turn_number": session['conversation_turns'] + 1
    }
    
    # 상태에 컨텍스트 추가
    state["_tool_context"] = tool_context
    
    try:
        # 에이전트 실행
        print("DEBUG: Attempting to invoke agent.")
        result = await agent.ainvoke(state)
        final_message = find_last_user_message(result["messages"], role="assistant")

        # 응답 시간 계산
        response_time_ms = int((time.time() - start_time) * 1000)

        # final_message가 None일 경우를 대비하여 기본 메시지 설정
        if final_message is None:
            final_message = "죄송합니다. 답변을 생성하지 못했습니다."
            logger.warning(f"에이전트가 응답을 생성하지 못했습니다. session_id={session['session_id']}")

        # 어시스턴트 메시지 저장 (도구 정보는 tool_wrapper에서 처리됨)
        chat_service.save_chat_message(
            session_id=session['session_id'],
            role="assistant",
            content=final_message,
            turn_number=session['conversation_turns'] + 1
        )
        
        # 세션 턴 수 업데이트
        chat_service.update_session_turns(session['session_id'])
        
        # API 호출 로그 저장
        chat_service.log_api_call(
            session_id=session['session_id'],
            endpoint="/v1/chat/completions",
            method="POST",
            request_data={"model": req.model, "message_count": len(req.messages)},
            response_status=200,
            response_time_ms=response_time_ms
        )
        
        if req.stream:
            # 스트리밍 응답
            return StreamingResponse(
                agent_stream_generator(req.model, final_message),
                media_type="text/event-stream",
                headers={"X-Session-ID": session['session_id']}
            )
        else:
            # 일반 JSON 응답
            return {
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": req.model,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": final_message}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},  # 사용량은 추적하지 않음
                "x_session_id": session['session_id']  # 세션 ID 반환
            }
            
    except Exception as e:
        # 오류 발생 시 로깅
        response_time_ms = int((time.time() - start_time) * 1000)
        error_message = str(e)
        
        chat_service.log_api_call(
            session_id=session['session_id'],
            endpoint="/v1/chat/completions",
            method="POST",
            request_data={"model": req.model, "message_count": len(req.messages)},
            response_status=500,
            response_time_ms=response_time_ms,
            error_message=error_message
        )
        
        logger.error(f"에이전트 실행 오류: {error_message}")
        raise HTTPException(status_code=500, detail=f"에이전트 실행 오류: {error_message}")


async def handle_llm_proxy_request(req: OpenAIChatRequest):
    """
    일반 LLM 모델 요청을 프록시합니다.
    
    Args:
        req: OpenAI 호환 채팅 요청
        
    Returns:
        프록시된 LLM 응답
    """
    try:
        # 모델 정보 확인
        model_info = get_model_info(req.model)
        if not model_info:
            raise HTTPException(
                status_code=400, 
                detail=f"지원하지 않는 모델입니다: {req.model}. 지원 모델 목록은 /v1/models 엔드포인트에서 확인하세요."
            )
        
        # 해당 모델의 프로바이더에 맞는 클라이언트 가져오기
        model_client = get_client_for_model(req.model)
        
        # 프로바이더별 클라이언트로 요청을 전달
        response = model_client.chat.completions.create(
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

    except ValueError as e:
        # 모델 또는 프로바이더 관련 오류
        raise HTTPException(status_code=400, detail=str(e))
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


@router.post(
    "/chat/completions",
    summary="AI 채팅 완성",
    description="""
    **OpenAI API와 호환되는 채팅 엔드포인트입니다.**
    
    요청된 모델 ID에 따라 다음과 같이 동작합니다:
    - **CoE 에이전트 모델**: LangGraph 기반 AI 에이전트 실행
    - **일반 LLM 모델**: OpenAI/Anthropic 등 외부 LLM API 프록시
    
    ### 🤖 지원 모델
    - `coe-agent-v1`: CoE LangGraph 에이전트 (추천)
    - `gpt-4`, `gpt-3.5-turbo`: OpenAI 모델
    - `claude-3-sonnet`: Anthropic 모델
    
    ### 📝 사용 예시
    ```bash
    curl -X POST "http://localhost:8000/v1/chat/completions" \\
      -H "Content-Type: application/json" \\
      -H "X-Session-ID: your-session-id" \\
      -d '{
        "model": "coe-agent-v1",
        "messages": [
          {"role": "user", "content": "안녕하세요! CoE 에이전트 기능을 테스트해보고 싶습니다."}
        ],
        "stream": false
      }'
    ```
    
    ### 🔄 스트리밍 지원
    `"stream": true` 설정으로 실시간 응답을 받을 수 있습니다.
    
    ### 📊 세션 관리
    `X-Session-ID` 헤더로 세션을 지정할 수 있습니다. 없으면 새 세션이 생성됩니다.
    """,
    response_description="채팅 완성 응답 (스트리밍 또는 JSON)"
)
async def chat_completions(req: OpenAIChatRequest, request: Request, db: Session = Depends(get_db)):
    """OpenAI API와 호환되는 채팅 엔드포인트 - CoE 에이전트 또는 외부 LLM 호출"""
    logger.info(f"채팅 요청 수신: model={req.model}, messages={len(req.messages)}")
    
    # 1. CoE 에이전트 모델을 요청한 경우
    if req.model == _agent_model_id:
        return await handle_agent_request(req, _agent, _agent_model_id, request, db)
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