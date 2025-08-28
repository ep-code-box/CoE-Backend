"""
스트리밍 응답 관련 유틸리티 함수들을 담당하는 모듈입니다.
OpenAI 호환 스트리밍 형식의 응답을 생성합니다.
"""

import json
import time
import uuid
import asyncio
from typing import AsyncGenerator, Dict, Any


def create_openai_chunk(model_id: str, delta: Dict[str, Any], finish_reason: str = None, session_id: str = None) -> str:
    """
    OpenAI 스트리밍 형식에 맞는 청크(chunk)를 생성합니다.
    
    Args:
        model_id: 모델 ID
        delta: 청크 내용 (예: {"content": "hello"}, {"tool_calls": [...]})
        finish_reason: 완료 이유 (None, "stop", "length", "tool_calls" 등)
        
    Returns:
        str: OpenAI 스트리밍 형식의 청크 문자열
    """
    chunk_id = f"chatcmpl-{uuid.uuid4()}"
    response = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model_id,
        "choices": [
            {
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason,
            }
        ],
    }
    if session_id:
        response["session_id"] = session_id
    return f"data: {json.dumps(response)}\n\n"


async def agent_stream_generator(model_id: str, final_message_dict: Dict[str, Any], session_id: str) -> AsyncGenerator[str, None]:
    """
    LangGraph 에이전트의 최종 응답을 스트리밍 형식으로 변환하는 비동기 생성기입니다.
    텍스트 응답과 도구 호출 응답을 모두 처리할 수 있습니다.
    """
    content = final_message_dict.get("content")
    tool_calls = final_message_dict.get("tool_calls")
    finish_reason = None
    has_sent_chunk = False

    # 1. 텍스트 콘텐츠 스트리밍
    if content:
        words = content.split(' ')
        for i, word in enumerate(words):
            session_id_to_send = session_id if not has_sent_chunk else None
            yield create_openai_chunk(model_id, {"content": f"{word} "}, session_id=session_id_to_send)
            has_sent_chunk = True
            await asyncio.sleep(0.05)  # 인위적인 딜레이로 스트리밍 효과 극대화
        finish_reason = "stop"

    # 2. 도구 호출 스트리밍 (단일 청크로 전송)
    if tool_calls:
        delta = {"role": "assistant", "content": None, "tool_calls": tool_calls}
        session_id_to_send = session_id if not has_sent_chunk else None
        yield create_openai_chunk(model_id, delta, session_id=session_id_to_send)
        finish_reason = "tool_calls"
    
    # 3. 스트림 종료를 알리는 마지막 청크
    yield create_openai_chunk(model_id, {}, finish_reason=finish_reason)
    yield "data: [DONE]\n\n"


async def proxy_stream_generator(response) -> AsyncGenerator[str, None]:
    """
    일반 LLM 응답을 프록시하여 스트리밍하는 비동기 생성기입니다.
    
    Args:
        response: OpenAI 클라이언트의 스트리밍 응답
        
    Yields:
        str: 프록시된 스트리밍 청크들
    """
    async for chunk in response:
        yield f"data: {chunk.model_dump_json()}\n\n"
