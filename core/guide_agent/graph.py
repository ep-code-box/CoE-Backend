"""Graph builder for the backend guide agent."""
from __future__ import annotations

from typing import Awaitable, Callable

from .nodes import advisor_node, feedback_node, knowledge_node, planner_node
from .state import GuideAgentState

try:  # pragma: no cover - executed when langgraph is available
    from langgraph.graph import END, StateGraph
except ImportError:  # pragma: no cover - sequential fallback path

    class _SequentialGraph:
        def __init__(
            self,
            nodes: tuple[Callable[[GuideAgentState], Awaitable[GuideAgentState]], ...],
        ) -> None:
            self._nodes = nodes

        async def ainvoke(self, state: GuideAgentState) -> GuideAgentState:
            current_state: GuideAgentState = dict(state)  # type: ignore[var-annotated]
            for node in self._nodes:
                update = await node(current_state)
                if update:
                    current_state.update(update)  # type: ignore[arg-type]
            return current_state

    def build_guide_agent_graph():
        return _SequentialGraph(
            (planner_node, knowledge_node, advisor_node, feedback_node)
        )

else:

    def build_guide_agent_graph():
        graph = StateGraph(GuideAgentState)
        graph.add_node("planner", planner_node)
        graph.add_node("knowledge", knowledge_node)
        graph.add_node("advisor", advisor_node)
        graph.add_node("feedback", feedback_node)

        graph.set_entry_point("planner")
        graph.add_edge("planner", "knowledge")
        graph.add_edge("knowledge", "advisor")
        graph.add_edge("advisor", "feedback")
        graph.add_edge("feedback", END)

        return graph.compile()
