"""High level wrapper for running the guide agent."""
from __future__ import annotations

import uuid
from typing import Iterable, Sequence

from .graph import build_guide_agent_graph
from .models import DeveloperContext, GuideAgentResult, GuidanceRecommendation, SessionMemory
from .state import GuideAgentState


class GuideAgent:
    def __init__(self, *, rag_client=None) -> None:
        self._graph = build_guide_agent_graph()
        self._rag_client = rag_client

    async def run(
        self,
        *,
        prompt: str,
        profile: str = "default",
        language: str = "ko",
        paths: Sequence[str] | None = None,
        memory: SessionMemory | None = None,
        metadata: dict[str, object] | None = None,
    ) -> GuideAgentResult:
        context = DeveloperContext(
            profile_name=profile,
            working_paths=tuple(paths or ()),
            language=language,
            metadata=metadata or {},
        )
        session_memory = memory or SessionMemory(session_id=str(uuid.uuid4()))

        initial_state: GuideAgentState = {
            "context": context,
            "memory": session_memory,
            "raw_request": {"prompt": prompt, "profile": profile},
        }
        if self._rag_client is not None:
            initial_state["rag_client"] = self._rag_client

        result_state = await self._graph.ainvoke(initial_state)
        return _state_to_result(result_state)


def _state_to_result(state: GuideAgentState) -> GuideAgentResult:
    plan = list(state.get("plan") or [])
    insights = list(state.get("insights") or [])
    recommendations = list(_coerce_recommendations(state.get("recommendations")))
    summary = state.get("summary") or "가이드가 준비되었습니다."
    memory = state.get("memory") or SessionMemory(session_id="transient")

    return GuideAgentResult(
        summary=summary,
        plan=tuple(plan),
        recommendations=tuple(recommendations),
        insights=tuple(insights),
        memory=memory,
    )


def _coerce_recommendations(value: object) -> Iterable[GuidanceRecommendation]:
    if not value:
        return ()
    if isinstance(value, GuidanceRecommendation):
        return (value,)
    if isinstance(value, Iterable):
        return tuple(value)  # type: ignore[arg-type]
    return ()
