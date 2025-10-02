"""Typed state shared across guide agent LangGraph nodes."""
from __future__ import annotations

from typing import Any, List

from typing_extensions import TypedDict

from .models import DeveloperContext, GuidanceRecommendation, SessionMemory


class GuideAgentState(TypedDict, total=False):
    context: DeveloperContext
    memory: SessionMemory
    plan: List[str]
    insights: List[str]
    recommendations: List[GuidanceRecommendation]
    raw_request: dict[str, Any]
    summary: str
    rag_client: Any
