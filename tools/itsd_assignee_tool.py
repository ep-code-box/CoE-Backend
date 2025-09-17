import os
from typing import Dict, Any, Optional, List

import httpx

from core.schemas import AgentState


# Prefer explicit URL via RAG_PIPELINE_URL, fallback to default service DNS in Compose
RAG_BASE = os.getenv("RAG_PIPELINE_URL", "http://ragpipeline:8001").rstrip("/")


async def run(tool_input: Optional[Dict[str, Any]], state: AgentState) -> Dict[str, Any]:
    """Call RAG ITSD recommender with title/description and return Markdown.

    If tool_input is missing, try to use the last user message as description.
    """
    # Extract inputs
    title = None
    description = None
    page = 1
    page_size = 5
    use_rrf: Optional[bool] = None
    w_title: Optional[float] = None
    w_content: Optional[float] = None
    rrf_k0: Optional[int] = None
    top_k_each: Optional[int] = None

    def _to_bool(value: Any) -> Optional[bool]:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes"}:
                return True
            if lowered in {"false", "0", "no"}:
                return False
        try:
            return bool(int(value))
        except Exception:
            return bool(value)

    if tool_input:
        title = tool_input.get("title")
        description = tool_input.get("description")
        page = int(tool_input.get("page", page))
        page_size = int(tool_input.get("page_size", page_size))
        # Optional fusion overrides
        if "use_rrf" in tool_input:
            use_rrf = _to_bool(tool_input.get("use_rrf"))
        if "w_title" in tool_input:
            try:
                w_title = float(tool_input.get("w_title"))
            except (TypeError, ValueError):
                w_title = None
        if "w_content" in tool_input:
            try:
                w_content = float(tool_input.get("w_content"))
            except (TypeError, ValueError):
                w_content = None
        if "rrf_k0" in tool_input:
            try:
                rrf_k0 = int(tool_input.get("rrf_k0"))
            except (TypeError, ValueError):
                rrf_k0 = None
        if "top_k_each" in tool_input:
            try:
                top_k_each = int(tool_input.get("top_k_each"))
            except (TypeError, ValueError):
                top_k_each = None

    # Fallbacks from conversation
    if not description:
        # Use last user message as description when not provided
        history = state.get("history") or []
        for msg in reversed(history):
            if msg.get("role") == "user" and msg.get("content"):
                description = msg["content"]
                break

    if not title:
        # Derive a short title from the first line of description
        if description:
            title = (description.splitlines() or [description])[0][:80]
        else:
            return {"messages": [{"role": "assistant", "content": "제목 또는 내용이 필요합니다."}]}

    url = f"{RAG_BASE}/api/v1/itsd/recommend-assignee"

    payload = {
        "title": title,
        "description": description,
    }
    params: Dict[str, Any] = {"page": page, "page_size": page_size}
    if use_rrf is not None:
        params["use_rrf"] = use_rrf
    if w_title is not None:
        params["w_title"] = w_title
    if w_content is not None:
        params["w_content"] = w_content
    if rrf_k0 is not None:
        params["rrf_k0"] = rrf_k0
    if top_k_each is not None:
        params["top_k_each"] = top_k_each

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload, params=params)
            resp.raise_for_status()
        # RAG returns a JSON string (Markdown content)
        content = resp.json()
        if not isinstance(content, str):
            content = str(content)
        return {"messages": [{"role": "assistant", "content": content}]}
    except httpx.HTTPStatusError as e:
        return {
            "messages": [
                {
                    "role": "assistant",
                    "content": f"ITSD 추천 호출 오류: {e.response.status_code} {e.response.text}",
                }
            ]
        }
    except httpx.RequestError as e:
        return {"messages": [{"role": "assistant", "content": f"ITSD 추천 호출 오류: {e}"}]}


# Tool schema exposed to the LLM
available_tools: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "itsd_recommend_assignee",
            "description": (
                "ITSD 신규 요청의 제목과 내용을 바탕으로 최적의 담당자를 추천합니다. "
                "제목/내용을 모두 주면 정확도가 높아집니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "요청 제목"},
                    "description": {"type": "string", "description": "요청 상세 내용"},
                    "page": {"type": "integer", "description": "페이지 (기본 1)"},
                    "page_size": {"type": "integer", "description": "페이지 크기 (기본 5, 최대 50)"},
                    "use_rrf": {
                        "type": "boolean",
                        "description": "Late Fusion 시 Reciprocal Rank Fusion 사용 여부",
                    },
                    "w_title": {
                        "type": "number",
                        "description": "타이틀 임베딩 가중치 (use_rrf가 false일 때 사용)",
                    },
                    "w_content": {
                        "type": "number",
                        "description": "본문 임베딩 가중치 (use_rrf가 false일 때 사용)",
                    },
                    "rrf_k0": {
                        "type": "integer",
                        "description": "RRF 결합 상수 k0",
                    },
                    "top_k_each": {
                        "type": "integer",
                        "description": "타이틀/본문 각각 검색할 상위 문서 수",
                    },
                },
                "required": ["title", "description"],
            },
        },
    }
]

tool_functions: Dict[str, Any] = {
    "itsd_recommend_assignee": run,
}
