import os
import requests
from typing import Dict, Any, Optional, List

from core.schemas import AgentState


# Prefer RAG_PIPELINE_URL, fallback to RAG_PIPELINE_BASE_URL, then default to service DNS
RAG_BASE = (
    os.getenv("RAG_PIPELINE_URL")
    or os.getenv("RAG_PIPELINE_BASE_URL")
    or "http://coe-ragpipeline:8001"
).rstrip("/")


async def run(tool_input: Optional[Dict[str, Any]], state: AgentState) -> Dict[str, Any]:
    """Call RAG ITSD recommender with title/description and return Markdown.

    If tool_input is missing, try to use the last user message as description.
    """
    # Extract inputs
    title = None
    description = None
    page = 1
    page_size = 5

    if tool_input:
        title = tool_input.get("title")
        description = tool_input.get("description")
        page = int(tool_input.get("page", page))
        page_size = int(tool_input.get("page_size", page_size))

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
    params = {"page": page, "page_size": page_size}

    try:
        resp = requests.post(url, json=payload, params=params, timeout=120)
        resp.raise_for_status()
        # RAG returns a JSON string (Markdown content)
        content = resp.json()
        if not isinstance(content, str):
            content = str(content)
        return {"messages": [{"role": "assistant", "content": content}]}
    except requests.RequestException as e:
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
                },
                "required": ["title", "description"],
            },
        },
    }
]

tool_functions: Dict[str, Any] = {
    "itsd_recommend_assignee": run,
}

# Contexts where this tool is available
tool_contexts: List[str] = ["openWebUi"]

# Map name → endpoint path (used to locate this tool from _map file)
endpoints = {
    "itsd_recommend_assignee": "/tools/itsd/recommend-assignee",
}
