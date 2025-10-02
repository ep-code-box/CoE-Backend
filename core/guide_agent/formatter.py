"""Utilities to format guide agent results for chat responses."""
from __future__ import annotations

from textwrap import dedent

from .models import GuideAgentResult


def format_result_as_markdown(result: GuideAgentResult) -> str:
    sections: list[str] = []

    sections.append(f"**요약**\n{result.summary.strip()}")

    if result.plan:
        plan_lines = "\n".join(f"- {item}" for item in result.plan)
        sections.append(f"**계획 체크리스트**\n{plan_lines}")

    if result.recommendations:
        rec_lines = []
        for rec in result.recommendations:
            rationale = "\n".join(f"    - {line}" for line in rec.rationale[:3]) if rec.rationale else "    - (근거 없음)"
            actions = "\n".join(f"    - {action}" for action in rec.actions) if rec.actions else "    - (권장 행동 없음)"
            rec_lines.append(
                dedent(
                    f"""
                    - **{rec.title}** ({rec.priority})
                      - 설명: {rec.detail}
                      - 근거:\n{rationale}
                      - 다음 행동:\n{actions}
                    """.rstrip()
                )
            )
        sections.append("**추천 사항**\n" + "\n".join(rec_lines))

    if result.insights:
        insight_lines = "\n".join(f"- {line}" for line in result.insights[:6])
        sections.append(f"**참고 인사이트**\n{insight_lines}")

    return "\n\n".join(sections)
