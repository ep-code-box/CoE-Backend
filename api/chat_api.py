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

from core.schemas import ChatRequest, ChatResponse, OpenAIChatRequest, AiderChatRequest
from core.llm_client import client, get_client_for_model, get_model_info
from core.database import get_db
from services.chat_service import get_chat_service
from utils.streaming_utils import agent_stream_generator, proxy_stream_generator
from tools.utils import find_last_user_message
import os # os 모듈 임포트
import requests # requests 모듈 임포트

logger = logging.getLogger(__name__)

# 전역 변수로 에이전트 정보 저장
_agent = None
_agent_model_id = None
_aider_agent = None
_aider_agent_model_id = None

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
    chat_service = get_chat_service(db)
    
    # 요청 본문에서 session_id 추출 또는 새로 생성
    session_id = req.session_id
    user_agent = request.headers.get("User-Agent")
    ip_address = request.client.host if request.client else None
    
    # 세션 생성 또는 조회
    session = chat_service.get_or_create_session(
        session_id=session_id,
        user_agent=user_agent,
        ip_address=ip_address
    )
    current_session_id = session['session_id']
    
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
            session_id=current_session_id,
            role="user",
            content=user_message,
            turn_number=session['conversation_turns'] + 1
        )
    
    # 에이전트 상태 준비
    state = {"messages": sanitized_messages}
    
    # 도구 선택 및 실행 정보를 추적하기 위한 컨텍스트 설정
    tool_context = {
        "session_id": current_session_id,
        "chat_service": chat_service,
        "turn_number": session['conversation_turns'] + 1
    }
    
    # 상태에 컨텍스트 추가
    state["_tool_context"] = tool_context
    
    try:
        logger.info(f"Attempting to invoke agent with state: {state.keys()}")
        # 에이전트 실행
        result = await agent.ainvoke(state)
        logger.info(f"Agent invocation successful. Result keys: {result.keys()}")
        final_message = find_last_user_message(result["messages"], role="assistant")

        # 응답 시간 계산
        response_time_ms = int((time.time() - start_time) * 1000)

        # final_message가 None일 경우를 대비하여 기본 메시지 설정
        if final_message is None:
            final_message = "죄송합니다. 답변을 생성하지 못했습니다."
            logger.warning(f"에이전트가 응답을 생성하지 못했습니다. session_id={current_session_id}")

        # 어시스턴트 메시지 저장 (도구 정보는 tool_wrapper에서 처리됨)
        chat_service.save_chat_message(
            session_id=current_session_id,
            role="assistant",
            content=final_message,
            turn_number=session['conversation_turns'] + 1
        )
        
        # 세션 턴 수 업데이트
        chat_service.update_session_turns(current_session_id)
        
        # API 호출 로그 저장
        chat_service.log_api_call(
            session_id=current_session_id,
            endpoint="/v1/chat/completions",
            method="POST",
            request_data={"model": req.model, "message_count": len(req.messages)},
            response_status=200,
            response_time_ms=response_time_ms
        )
        
        if req.stream:
            # 스트리밍 응답
            return StreamingResponse(
                agent_stream_generator(req.model, final_message, current_session_id),
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
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "session_id": current_session_id
            }
            
    except Exception as e:
        # 오류 발생 시 로깅
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
            return response

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


def set_aider_agent_info(agent, agent_model_id: str):
    """
    Aider 에이전트 정보를 전역 변수에 설정합니다.
    
    Args:
        agent: 컴파일된 LangGraph 에이전트
        agent_model_id: 에이전트 모델 ID
    """
    global _aider_agent, _aider_agent_model_id
    _aider_agent = agent
    _aider_agent_model_id = agent_model_id


@router.post(
    "/chat/completions",
    summary="AI 채팅 API (OpenAI 호환)",
    description="""
    **OpenAI의 Chat Completions API와 호환되는 AI 에이전트 채팅 엔드포인트입니다.**

    이 엔드포인트는 요청된 `model`에 따라 두 가지 방식으로 동작합니다:
    1.  **CoE 에이전트 모델 (`coe-agent-v1`)**: LangGraph로 구축된 내부 AI 에이전트를 호출하여, 등록된 도구를 사용한 복잡한 작업 수행이 가능합니다.
    2.  **일반 LLM 모델 (예: `gpt-4o-mini`)**: 외부 LLM API(OpenAI, Anthropic 등)를 직접 호출하는 프록시 역할을 합니다.

    ### 🔄 세션 관리 (대화 연속성)
    - **첫 요청**: `session_id` 없이 요청하면, 서버가 새로운 `session_id`를 생성하여 응답 본문에 포함해 반환합니다.
    - **대화 이어가기**: 다음 요청부터는 이 `session_id`를 요청 본문에 포함시켜 보내야 이전 대화의 맥락을 유지할 수 있습니다.

    ### 🤖 지원 모델
    - `coe-agent-v1`: CoE LangGraph 에이전트 (내부 도구 사용)
    - `gpt-4o-mini`, `gpt-4o`: OpenAI 모델 프록시
    - `claude-3-sonnet-20240229`: Anthropic 모델 프록시
    - 전체 목록은 `/v1/models` API를 통해 확인할 수 있습니다.

    ### 📝 사용 예시 (cURL)
    ```bash
    # 1. 첫 번째 요청 (세션 시작)
    curl -X POST "http://localhost:8000/v1/chat/completions" \\
      -H "Content-Type: application/json" \\
      -d '{
        "model": "coe-agent-v1",
        "messages": [{"role": "user", "content": "LangGraph가 뭐야?"}]
      }' # 응답에서 session_id 확인

    # 2. 두 번째 요청 (대화 이어가기)
    curl -X POST "http://localhost:8000/v1/chat/completions" \\
      -H "Content-Type: application/json" \\
      -d '{
        "model": "coe-agent-v1",
        "session_id": "여기에_받은_세션ID를_입력하세요",
        "messages": [{"role": "user", "content": "그것의 장점은 뭐야?"}]
      }'
    ```
    """,
    response_description="채팅 완성 응답. 스트리밍 시 `text/event-stream`, 아닐 경우 `application/json`."
)
@router.post(
    "/chat/completions/aider",
    summary="AI 채팅 API (aider 전용, RAG 그룹 필터링)",
    description="""
    **aider와 같은 클라이언트를 위한 OpenAI Chat Completions API 호환 엔드포인트입니다.**
    `group_name`을 사용하여 RAG(Retrieval-Augmented Generation) 검색을 특정 그룹의 데이터로 필터링합니다.

    ### 🔄 세션 관리 (대화 연속성)
    - **첫 요청**: `session_id` 없이 요청하면, 서버가 새로운 `session_id`를 생성하여 응답 본문에 포함해 반환합니다.
    - **대화 이어가기**: 다음 요청부터는 이 `session_id`를 요청 본문에 포함시켜 보내야 이전 대화의 맥락을 유지할 수 있습니다.

    ### 🤖 지원 모델
    - `ax4`: sk Adot 4 모델 사용
    - `gpt-4o-mini`, `gpt-4o`: OpenAI 모델 프록시
    - 전체 목록은 `/v1/models` API를 통해 확인할 수 있습니다.

    ### 📝 사용 예시 (cURL)
    ```bash
    # 1. 첫 번째 요청 (세션 시작, group_name 포함)
    curl -X POST "http://localhost:8000/v1/chat/completions/aider" \
      -H "Content-Type: application/json" \
      -d '{ 
        "model": "ax4",
        "messages": [{"role": "user", "content": "payment 모듈의 코드 구조에 대해 알려줘"}],
        "group_name": "swing"
      }' # 응답에서 session_id 확인

    # 2. 두 번째 요청 (대화 이어가기, group_name 포함)
    curl -X POST "http://localhost:8000/v1/chat/completions/aider" \
      -H "Content-Type: application/json" \
      -d '{ 
        "model": "ax4",
        "session_id": "여기에_받은_세션ID를_입력하세요",
        "messages": [{"role": "user", "content": "그것의 장점은 뭐야?"}],
        "group_name": "swing"
      }'
    ```
    """,
    response_description="채팅 완성 응답. 스트리밍 시 `text/event-stream`, 아닐 경우 `application/json`."
)
async def chat_completions_aider(req: AiderChatRequest, request: Request, db: Session = Depends(get_db)):
    """OpenAI API와 호환되는 채팅 엔드포인트 - CoE 에이전트 또는 외부 LLM 호출 (RAG 그룹 필터링)"""
    logger.info(f"채팅 요청 수신 (aider 전용): model={req.model}, messages={len(req.messages)}, session_id={req.session_id}, group_name={req.group_name})")

    # RAG 검색 로직
    rag_context = ""
    user_message_content = find_last_user_message(req.messages)

    if req.group_name is None:
        req.group_name = "swing"

    if user_message_content and req.group_name:
        # RAG 검색이 필요한 질의인지 판단 (간단한 키워드 매칭)
        rag_keywords = ["코드", "분석", "정보", "구조", "기능", "어떻게", "설명", "예시", "모듈", "클래스", "함수", "파일"]
        if any(keyword in user_message_content for keyword in rag_keywords):
            try:
                rag_pipeline_base_url = os.getenv("RAG_PIPELINE_BASE_URL", "http://localhost:8001")
                rag_search_url = f"{rag_pipeline_base_url}/api/v1/search"

                search_payload = {
                    "query": user_message_content,
                    "k": 3, # 상위 3개 문서 검색
                    "filter_metadata": {"group_name": req.group_name}
                }
                
                logger.info(f"RAG 검색 요청: {rag_search_url}, payload: {search_payload}")
                rag_response = requests.post(rag_search_url, json=search_payload)
                rag_response.raise_for_status()
                
                rag_results = rag_response.json()
                
                if rag_results:
                    rag_context = "\n\n--- 관련 코드/문서 ---\n"
                    for doc in rag_results:
                        rag_context += f"파일: {doc['metadata'].get('file_path', 'N/A')}\n"
                        rag_context += f"내용: {doc['content']}\n---\n"
                    logger.info(f"RAG 검색 결과 {len(rag_results)}개 발견.")
                else:
                    logger.info("RAG 검색 결과 없음.")

            except Exception as e:
                logger.error(f"RAG 검색 중 오류 발생: {e}")
                rag_context = f"RAG 검색 중 오류가 발생했습니다: {str(e)}"
    
    # 원본 메시지에 RAG 컨텍스트 추가
    messages_to_process = req.messages
    if rag_context:
        # 마지막 사용자 메시지에 컨텍스트 추가
        for i in range(len(messages_to_process) - 1, -1, -1):
            if messages_to_process[i].role == "user":
                messages_to_process[i].content += rag_context
                break
        logger.info("RAG 컨텍스트가 사용자 메시지에 추가되었습니다.")
    else:
        # RAG 검색 결과가 없을 경우, 에이전트에게 안내 메시지 추가
        logger.info("RAG 검색 결과가 없어 안내 메시지를 추가합니다.")
        for i in range(len(messages_to_process) - 1, -1, -1):
            if messages_to_process[i].role == "user":
                messages_to_process[i].content += "\n\n[중요]: 저장된 문서에서 요청하신 내용에 대한 관련 정보를 찾을 수 없습니다. 이 질문에 대해 아는 바가 없다면 '관련 정보를 찾을 수 없습니다.'라고 답변하거나, 일반적인 지식으로 답변해주세요. 절대로 없는 정보를 지어내지 마세요."
                break

    # req 객체의 messages를 업데이트된 메시지로 교체
    req.messages = messages_to_process

    # 1. CoE 에이전트 모델을 요청한 경우
    if req.model == _aider_agent_model_id:
        return await handle_agent_request(req, _aider_agent, _aider_agent_model_id, request, db)
    # 2. 일반 LLM 모델을 요청한 경우 (프록시 역할)
    else:
        return await handle_llm_proxy_request(req)



@router.post("/chat", response_model=ChatResponse, deprecated=True, summary="[Deprecated] Use /v1/chat/completions instead")
async def legacy_chat_endpoint(req: ChatRequest):
    """이 엔드포인트는 더 이상 사용되지 않습니다. /v1/chat/completions를 사용하세요."""
    state = {"messages": [msg.model_dump() for msg in req.messages]}
    result = await _agent.ainvoke(state)
    return ChatResponse(messages=result["messages"])


def create_chat_router():
    """
    채팅 라우터를 생성합니다.
    
    Returns:
        APIRouter: 설정된 채팅 라우터
    """
    return router