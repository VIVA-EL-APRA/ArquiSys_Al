from __future__ import annotations

from arquisys_ai.agents.analyst_agent import AnalystAgent
from arquisys_ai.agents.architect_agent import ArchitectAgent
from arquisys_ai.core.models import PipelineResult


class ArquiSysWorkflow:
    def __init__(self, analyst_agent: AnalystAgent | None = None, architect_agent: ArchitectAgent | None = None):
        self._analyst_agent = analyst_agent or AnalystAgent()
        self._architect_agent = architect_agent or ArchitectAgent()

    def run(self, user_request: str) -> PipelineResult:
        analysis = self._analyst_agent.analyze(user_request)

        if not analysis.ready_for_architect:
            return PipelineResult(analysis=analysis, architecture=None)

        architecture = self._architect_agent.build(analysis)
        return PipelineResult(analysis=analysis, architecture=architecture)


def build_langgraph_workflow() -> object:
    """
    Placeholder for a LangGraph implementation.
    This base keeps a deterministic workflow while Sprint 2 hardens agents.
    """
    try:
        from langgraph.graph import END, StateGraph
    except ImportError as exc:
        raise RuntimeError("LangGraph is not installed. Install langgraph to use this workflow.") from exc

    from arquisys_ai.graph.state import WorkflowState

    analyst = AnalystAgent()
    architect = ArchitectAgent()

    def analyst_node(state: WorkflowState) -> WorkflowState:
        analysis = analyst.analyze(state["user_request"])
        return {**state, "analysis": analysis, "status": "analysis_done"}

    def architect_node(state: WorkflowState) -> WorkflowState:
        analysis = state["analysis"]
        if analysis is None or not analysis.ready_for_architect:
            return {**state, "architecture": None, "status": "need_more_context"}
        architecture = architect.build(analysis)
        return {**state, "architecture": architecture, "status": "done"}

    graph = StateGraph(WorkflowState)
    graph.add_node("analyst", analyst_node)
    graph.add_node("architect", architect_node)
    graph.set_entry_point("analyst")
    graph.add_edge("analyst", "architect")
    graph.add_edge("architect", END)
    return graph.compile()
