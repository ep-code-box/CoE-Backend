"""
SKT Chat API 어댑터

sktchat provider의 비-OpenAI 호환 API를 호출하고
응답을 OpenAI 호환 형식으로 변환합니다.

요청 변환:
  OpenAI messages[] → sktchat {"user_id", "model_cd", "message", "stream"}

응답 변환:
  sktchat NDJSON (token/error/carousel_list/chat_history_id)
  → OpenAI ChatCompletion 형식
"""
import json
import os
import time
import uuid
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

SKTCHAT_USER_ID = os.getenv("SKTCHAT_USER_ID", "coe_backend")


class SktchatApiError(Exception):
    """sktchat API 오류"""
    def __init__(self, status_code: str, reason: str, detects: Optional[list] = None):
        self.status_code = status_code
        self.reason = reason
        self.detects = detects
        super().__init__(f"sktchat API error [{status_code}]: {reason}")


def _extract_last_user_message(messages: List[Dict[str, Any]]) -> str:
    """OpenAI messages 배열에서 마지막 사용자 메시지를 추출합니다."""
    for msg in reversed(messages):
        role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", None)
        if role == "user":
            content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
            if isinstance(content, str):
                return content
            # content가 list인 경우 (multimodal)
            if isinstance(content, list):
                return " ".join(
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict) and part.get("type") == "text"
                )
    return ""


def _parse_ndjson_response(raw_text: str) -> str:
    """NDJSON 응답에서 token 데이터를 추출하여 전체 텍스트를 반환합니다."""
    content_parts: List[str] = []

    for line in raw_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("[SKTCHAT] Failed to parse response line: %s", line[:100])
            continue

        event_type = event.get("type")

        if event_type == "error":
            raise SktchatApiError(
                status_code=str(event.get("status_code", "500")),
                reason=event.get("reason", "Unknown error"),
                detects=event.get("detects"),
            )

        if event_type == "token":
            content_parts.append(str(event.get("data", "")))

        # carousel_list, chat_history_id 등은 현재 무시 (필요 시 확장 가능)

    return "".join(content_parts)


def _build_openai_response(model_cd: str, content: str) -> Dict[str, Any]:
    """OpenAI ChatCompletion 호환 응답 dict를 생성합니다."""
    return {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_cd,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }


async def call_sktchat_api(
    *,
    base_url: str,
    api_key: str,
    model_cd: str,
    messages: List[Dict[str, Any]],
    stream: bool = False,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    sktchat API를 호출하고 OpenAI 호환 응답으로 변환합니다.

    Args:
        base_url: sktchat API 베이스 URL (models.json의 api_base)
        api_key: X-AGENT-API-KEY 헤더 값
        model_cd: provider_model_id (sktchat의 model_cd 파라미터)
        messages: OpenAI 형식 메시지 배열
        stream: 스트리밍 여부
        user_id: sktchat user_id (기본: 환경변수 SKTCHAT_USER_ID)

    Returns:
        OpenAI ChatCompletion 호환 dict
    """
    user_message = _extract_last_user_message(messages)

    endpoint = f"{base_url.rstrip('/')}/api/agent/v1/chats"

    payload = {
        "user_id": user_id or SKTCHAT_USER_ID,
        "model_cd": model_cd,
        "message": user_message,
        "stream": stream,
    }

    headers = {
        "X-AGENT-API-KEY": api_key,
        "Content-Type": "application/json",
    }

    logger.info(
        "[SKTCHAT] POST %s | model_cd=%s user_id=%s",
        endpoint,
        model_cd,
        payload["user_id"],
    )

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()

        full_content = _parse_ndjson_response(response.text)

    return _build_openai_response(model_cd, full_content)


async def stream_sktchat_api(
    *,
    base_url: str,
    api_key: str,
    model_cd: str,
    messages: List[Dict[str, Any]],
    user_id: Optional[str] = None,
) -> AsyncIterator[str]:
    """
    sktchat API를 스트리밍 호출하고 OpenAI SSE 형식으로 변환합니다.

    Yields:
        OpenAI SSE 형식 문자열 (data: {...}\\n\\n)
    """
    user_message = _extract_last_user_message(messages)

    endpoint = f"{base_url.rstrip('/')}/api/agent/v1/chats"

    payload = {
        "user_id": user_id or SKTCHAT_USER_ID,
        "model_cd": model_cd,
        "message": user_message,
        "stream": True,
    }

    headers = {
        "X-AGENT-API-KEY": api_key,
        "Content-Type": "application/json",
    }

    logger.info(
        "[SKTCHAT][STREAM] POST %s | model_cd=%s",
        endpoint,
        model_cd,
    )

    completion_id = f"chatcmpl-{uuid.uuid4()}"
    created = int(time.time())

    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream("POST", endpoint, json=payload, headers=headers) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                line = line.strip()
                if not line:
                    continue

                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                event_type = event.get("type")

                if event_type == "error":
                    # 에러를 SSE로 전달 후 종료
                    error_msg = event.get("reason", "Unknown error")
                    error_chunk = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model_cd,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": f"\n[Error: {error_msg}]"},
                                "finish_reason": "stop",
                            }
                        ],
                    }
                    yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                    return

                if event_type == "token":
                    token_data = str(event.get("data", ""))
                    chunk = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model_cd,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": token_data},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

    # 스트림 종료
    final_chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model_cd,
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }
        ],
    }
    yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"
