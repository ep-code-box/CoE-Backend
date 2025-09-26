from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from pydantic import ValidationError

from core.schemas import AgentState
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from api.rag_api import EmbedContentPayload, embed_content as api_embed_content

CODE_BLOCK_PATTERN = re.compile(r"```(?:[^\n]*\n)?([\s\S]*?)```", re.MULTILINE)
MAX_ANALYSIS_CHARS = 4000


CONTENT_ANALYSIS_PROMPT = ChatPromptTemplate.from_template(
    """당신은 숙련된 소프트웨어 아키텍트입니다. 제공된 문서 내용을 분석하여 다음을 정리하세요:

1. 문서 요약 (3~5문장)
2. 핵심 구현/설계 포인트
3. 잠재적 위험 요소 또는 개선 여지
4. 후속 작업이나 확인이 필요한 TODO

가능하면 항목별로 bullet 형태로 답변하고, 문서에서 확인할 수 없는 내용은 추측하지 마세요.

---
문서 제목: {title}
문서 내용:
{content}
---
사용자 요청:
{question}
"""
)


def _extract_code_blocks(text: str) -> List[str]:
    matches = CODE_BLOCK_PATTERN.findall(text or "")
    return [m.strip() for m in matches if m.strip()]


def _extract_named_content(text: str) -> Optional[str]:
    pattern = re.compile(r"(?:파일(?:명|내용)?|content|내용)\s*[:：]\s*(.+)", re.IGNORECASE | re.DOTALL)
    match = pattern.search(text)
    if match:
        candidate = match.group(1).strip()
        return candidate if candidate else None
    return None


def _guess_title(text: str, default: str = "사용자 제공 문서") -> str:
    explicit = re.search(r"(?:파일명|file name|title)\s*[:：]\s*([^\n]+)", text, re.IGNORECASE)
    if explicit:
        title = explicit.group(1).strip()
        if title:
            return title

    filename = re.search(r"([\w\-\.]+\.[A-Za-z0-9]{1,8})\s*파일", text)
    if filename:
        title = filename.group(1).strip()
        if title:
            return title

    return default


def _extract_content_from_user_message(message: str) -> Optional[str]:
    if not message:
        return None

    blocks = _extract_code_blocks(message)
    if blocks:
        return "\n\n".join(blocks)

    named = _extract_named_content(message)
    if named:
        return named

    cleaned = message.strip()
    if len(cleaned) > 200 and "\n" in cleaned:
        return cleaned

    return None


def _coerce_metadata(value: Any) -> Optional[Dict[str, Any]]:
    if isinstance(value, dict):
        return value
    return None


async def run(tool_input: Optional[Dict[str, Any]], state: AgentState) -> Dict[str, Any]:
    user_message = state.get("input", "")
    question = user_message

    content = (tool_input or {}).get("content") if tool_input else None
    if not content:
        content = _extract_content_from_user_message(user_message)

    if not content or len(content.strip()) < 20:
        return {
            "messages": [{
                "role": "assistant",
                "content": "분석할 문서 내용을 찾지 못했습니다. 문서 본문을 함께 제공하거나 `content` 파라미터로 전달해주세요.",
            }]
        }

    title = (tool_input or {}).get("title") if tool_input else None
    if not title:
        title = _guess_title(user_message)

    group_name = (tool_input or {}).get("group_name") if tool_input else None
    metadata = _coerce_metadata((tool_input or {}).get("metadata") if tool_input else None)

    source_type = (tool_input or {}).get("source_type") if tool_input else None
    if source_type not in {"text", "file", "url"}:
        source_type = "text"

    source_data = (tool_input or {}).get("source_data") if tool_input else None
    if source_type == "text" or not source_data:
        source_data = content

    payload = EmbedContentPayload(
        source_type=source_type,
        source_data=source_data,
        group_name=group_name,
        title=title,
        metadata=metadata,
    )

    embed_result: Optional[Dict[str, Any]] = None
    embed_error: Optional[Dict[str, Any]] = None

    try:
        embed_result = await api_embed_content(payload)
    except ValidationError as exc:
        embed_error = {"message": f"요청 값 검증에 실패했습니다: {exc}"}
    except HTTPException as exc:
        embed_error = {"status_code": exc.status_code, "detail": exc.detail}
    except Exception as exc:
        embed_error = {"message": str(exc)}

    truncated_content = content[:MAX_ANALYSIS_CHARS]

    try:
        from core.llm_client import langchain_client

        chain = CONTENT_ANALYSIS_PROMPT | langchain_client | StrOutputParser()
        analysis = chain.invoke({
            "title": title,
            "content": truncated_content,
            "question": question,
        })
    except Exception as exc:
        analysis = f"문서 분석 중 오류가 발생했습니다: {exc}"

    status_line = "임베딩을 수행하지 않았습니다."
    if embed_result:
        count_text = embed_result.get("count")
        source_identifier = embed_result.get("source_identifier")
        status_line = (
            "임베딩 상태: 성공\n"
            f"저장 청크 수: {count_text}\n"
            f"저장 식별자: {source_identifier}"
        )
    elif embed_error:
        detail = embed_error.get("detail") or embed_error.get("message") or embed_error
        status_line = f"임베딩 실패: {detail}"

    response_content = (
        "📄 **문서 임베딩 및 분석 결과**\n\n"
        f"**제목**: {title}\n"
        f"**그룹**: {group_name or '-'}\n"
        f"{status_line}\n\n"
        f"{analysis}"
    )

    result_payload: Dict[str, Any] = {
        "messages": [{"role": "assistant", "content": response_content}],
        "analysis": analysis,
        "title": title,
        "group_name": group_name,
    }

    if embed_result:
        result_payload["embed_result"] = embed_result
    if embed_error:
        result_payload["embed_error"] = embed_error

    return result_payload


available_tools: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "rag_content_tool",
            "description": "문서 텍스트를 벡터DB에 저장하고 요약/분석합니다. 대량 텍스트나 파일 내용을 전달할 때 사용하세요.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "직접 제공할 문서 본문 텍스트"
                    },
                    "title": {
                        "type": "string",
                        "description": "문서를 식별할 제목"
                    },
                    "group_name": {
                        "type": "string",
                        "description": "문서를 그룹핑할 이름 (선택 사항)"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "추가 메타데이터 (선택 사항)"
                    },
                    "source_type": {
                        "type": "string",
                        "enum": ["text", "file", "url"],
                        "description": "콘텐츠 종류 (기본값 text)"
                    },
                    "source_data": {
                        "type": "string",
                        "description": "파일 경로 또는 URL 임베딩 시 사용할 원본 정보"
                    }
                }
            }
        }
    }
]


tool_functions: Dict[str, callable] = {
    "rag_content_tool": run,
}


tool_contexts: List[str] = ["rag", "document"]
