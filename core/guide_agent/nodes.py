"""Execution nodes that power the backend guide agent."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Iterable, List

from .models import DeveloperContext, GuidanceRecommendation, SessionMemory
from .rag_client import RagClient
from .state import GuideAgentState

logger = logging.getLogger(__name__)


async def planner_node(state: GuideAgentState) -> GuideAgentState:
    raw_request = state.get("raw_request") or {}
    prompt = str(raw_request.get("prompt", "")).strip()
    context = state.get("context") or DeveloperContext(profile_name="default")

    if state.get("plan"):
        return {}

    plan: List[str] = [
        "요청 의도 분석",
        "관련 가이드라인/문서 조회",
        "실행 가능한 권장 사항 정리",
    ]
    if context.working_paths:
        plan.append(f"대상 파일 {len(context.working_paths)}개 점검")
    if prompt:
        plan.append("사용자 질문 맞춤 설명 작성")

    logger.debug("planner_node.plan", extra={"plan": plan, "profile": context.profile_name})
    return {"plan": plan}


async def knowledge_node(state: GuideAgentState) -> GuideAgentState:
    insights = list(state.get("insights") or [])
    if insights:
        return {}

    context = state.get("context") or DeveloperContext(profile_name="default")
    doc_snippets = await asyncio.to_thread(_load_doc_highlights)
    rag_client = _extract_rag_client(state)
    prompt = str((state.get("raw_request") or {}).get("prompt", "")).strip()

    if context.language == "en":
        insights.extend(doc_snippets.get("en", []))
    else:
        insights.extend(doc_snippets.get("ko", []))

    if rag_client and prompt:
        rag_insights = await _gather_rag_insights(rag_client, prompt, context)
        insights.extend(rag_insights)

    if context.working_paths:
        paths = ", ".join(context.working_paths[:3])
        insights.append(f"현재 검토 중인 파일: {paths}")

    logger.debug("knowledge_node.insights", extra={"insight_count": len(insights)})
    return {"insights": insights}


async def advisor_node(state: GuideAgentState) -> GuideAgentState:
    if state.get("recommendations"):
        return {}

    plan = state.get("plan") or []
    insights = state.get("insights") or []
    context = state.get("context") or DeveloperContext(profile_name="default")

    recommendations: List[GuidanceRecommendation] = []
    if plan:
        recommendations.append(
            GuidanceRecommendation(
                title="계획 다시 확인",
                detail="아래 단계대로 진행하면 요청을 안정적으로 마무리할 수 있습니다.",
                rationale=tuple(plan),
                actions=tuple(plan[:3]),
                priority="high",
                tags=("plan", "focus"),
            )
        )

    if insights:
        recommendations.append(
            GuidanceRecommendation(
                title="관련 레퍼런스 확인",
                detail="문서 하이라이트를 검토하며 구현 방향을 조정하세요.",
                rationale=tuple(insights[:3]),
                actions=("필수 문서를 열람하고 체크리스트를 업데이트",),
                priority="medium",
                tags=("docs", "context"),
            )
        )

    if context.working_paths:
        recommendations.append(
            GuidanceRecommendation(
                title="파일별 가이드 적용",
                detail="선택된 파일에 스타일·테스트 규칙을 반영하세요.",
                rationale=("작업 대상 파일 정보를 기반으로 자동 생성된 권장 사항입니다.",),
                actions=tuple(f"{path} 검토" for path in context.working_paths),
                priority="medium",
                tags=("code", "style"),
            )
        )

    if not recommendations:
        recommendations.append(
            GuidanceRecommendation(
                title="정보 부족",
                detail="추가 컨텍스트나 파일 정보를 제공하면 더 정교한 가이드를 생성할 수 있습니다.",
                rationale=("현재 제공된 입력으로는 계획과 통찰을 구성하기 어렵습니다.",),
                actions=("변경하려는 파일 경로", "필요한 산출물 유형"),
                priority="low",
                tags=("next-step",),
            )
        )

    logger.debug("advisor_node.recommendations", extra={"count": len(recommendations)})
    return {"recommendations": recommendations}


async def feedback_node(state: GuideAgentState) -> GuideAgentState:
    recommendations = state.get("recommendations") or []
    memory = state.get("memory") or SessionMemory(session_id="transient")

    accepted_titles = [rec.title for rec in recommendations]
    summary_lines: List[str] = ["다음 단계 권장 사항이 준비되었습니다."]
    for rec in recommendations:
        summary_lines.append(f"- {rec.title} ({rec.priority})")

    updated_memory = SessionMemory(
        session_id=memory.session_id,
        recent_summary="\n".join(summary_lines),
        acknowledged_recommendations=tuple(accepted_titles),
        pending_questions=memory.pending_questions,
        preferences=memory.preferences,
    )

    logger.debug("feedback_node.summary", extra={"summary": summary_lines[0]})
    return {"summary": summary_lines[0], "memory": updated_memory}


def _load_doc_highlights() -> dict[str, List[str]]:
    ko_snippets: List[str] = []
    en_snippets: List[str] = []
    backend_root = Path(__file__).resolve().parents[2]
    repo_root = backend_root.parent
    doc_root_env = os.getenv("GUIDE_AGENT_DOC_ROOT")
    env_doc_path = Path(doc_root_env) if doc_root_env else None
    candidates: List[tuple[str, Path]] = [
        ("ko", backend_root / "AGENTS.md"),
        ("en", backend_root / "README.md"),
    ]
    if env_doc_path:
        candidates.append(("ko", env_doc_path / "guide_agent_brief.md"))
    candidates.append(("ko", repo_root / "CoE-Agent" / "docs" / "guide_agent_brief.md"))

    for language, path in candidates:
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        highlights = lines[:3]
        if language == "ko":
            ko_snippets.extend(highlights)
        else:
            en_snippets.extend(highlights)

    ko_snippets = list(dict.fromkeys(ko_snippets))
    en_snippets = list(dict.fromkeys(en_snippets))
    return {"ko": ko_snippets[:6], "en": en_snippets[:6]}


def _extract_rag_client(state: GuideAgentState) -> RagClient | None:
    rag_client = state.get("rag_client")
    if isinstance(rag_client, RagClient):
        return rag_client
    if hasattr(rag_client, "semantic_search"):
        return rag_client  # type: ignore[return-value]
    return None


async def _gather_rag_insights(
    rag_client: RagClient,
    prompt: str,
    context: DeveloperContext,
) -> List[str]:
    snippets: List[str] = []
    try:
        results = await rag_client.semantic_search(
            query=prompt,
            k=3,
            group_name=context.metadata.get("group_name") if context.metadata else None,
        )
        for entry in results:
            metadata = entry.get("metadata") or {}
            label = metadata.get("file_path") or metadata.get("document_type")
            prefix = f"[{label}] " if label else ""
            snippets.append(f"{prefix}{entry.get('content', '')}")
    except Exception as exc:  # pragma: no cover - network failure fallback
        logger.warning("knowledge_node.rag_failed", extra={"error": str(exc)})
    return snippets
