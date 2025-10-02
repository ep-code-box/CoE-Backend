"""Data models backing the guide agent pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Sequence


@dataclass(slots=True)
class DeveloperContext:
    """Execution backdrop and user preferences for the guide agent."""

    profile_name: str
    working_paths: tuple[str, ...] = ()
    target_branch: str | None = None
    language: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(slots=True)
class GuidanceRecommendation:
    """Single actionable recommendation produced by the agent."""

    title: str
    detail: str
    rationale: tuple[str, ...] = ()
    actions: tuple[str, ...] = ()
    priority: Literal["high", "medium", "low"] = "medium"
    tags: tuple[str, ...] = ()


@dataclass(slots=True)
class SessionMemory:
    """Lightweight memory shared across guide agent nodes."""

    session_id: str
    recent_summary: str = ""
    acknowledged_recommendations: tuple[str, ...] = ()
    pending_questions: tuple[str, ...] = ()
    preferences: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GuideAgentResult:
    """Aggregated output returned by the guide agent run."""

    summary: str
    plan: Sequence[str]
    recommendations: Sequence[GuidanceRecommendation]
    insights: Sequence[str]
    memory: SessionMemory
