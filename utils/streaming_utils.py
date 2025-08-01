"""
스트리밍 응답 관련 유틸리티 함수들을 담당하는 모듈입니다.
OpenAI 호환 스트리밍 형식의 응답을 생성합니다.
"""

import json
import time
import uuid
import asyncio
from typing import AsyncGenerator


def create_openai_chunk(model_id: str, content: str, finish_reason: str = None) -> str:
    """
    OpenAI 스트리밍 형식에 맞는 청크(chunk)를 생성합니다.
    
    Args:
        model_id: 모델 ID
        content: 청크 내용
        finish_reason: 완료 이유 (None, "stop", "length" 등)
        
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
                "delta": {"content": content},
                "finish_reason": finish_reason,
            }
        ],
    }
    return f"data: {json.dumps(response)}\n\n"


async def agent_stream_generator(model_id: str, final_message: str) -> AsyncGenerator[str, None]:
    """
    LangGraph 에이전트의 최종 응답을 스트리밍 형식으로 변환하는 비동기 생성기입니다.
    
    Args:
        model_id: 모델 ID
        final_message: 스트리밍할 최종 메시지
        
    Yields:
        str: OpenAI 스트리밍 형식의 청크들
    """
    # 메시지를 단어 단위로 나누어 스트리밍 효과를 냅니다.
    words = final_message.split(' ')
    for word in words:
        yield create_openai_chunk(model_id, f"{word} ")
        await asyncio.sleep(0.05)  # 인위적인 딜레이로 스트리밍 효과 극대화
    
    # 스트림 종료를 알리는 마지막 청크
    yield create_openai_chunk(model_id, "", "stop")
    yield "data: [DONE]\n\n"


async def proxy_stream_generator(response) -> AsyncGenerator[str, None]:
    """
    일반 LLM 응답을 프록시하여 스트리밍하는 비동기 생성기입니다.
    
    Args:
        response: OpenAI 클라이언트의 스트리밍 응답
        
    Yields:
        str: 프록시된 스트리밍 청크들
    """
    for chunk in response:
        yield f"data: {chunk.model_dump_json()}\n\n"