"""LangGraph `State` definition for the finance assistant workflow."""

from __future__ import annotations

from typing import Annotated, Any

from typing_extensions import NotRequired, TypedDict

from workflow.reducers import RESET_AGENT_OUTPUTS, merge_agent_outputs

__all__ = ["GraphState", "RESET_AGENT_OUTPUTS"]


class GraphState(TypedDict, total=False):
    """Shared graph state: orchestration output, parallel specialist merges, and UI inputs."""

    user_query: str
    conversation_context: str
    user_profile_json: str
    rag_context: str
    market_context: str
    orchestration: dict[str, Any]
    # Populated by each parallel `Send("specialist", {"agent_job": ...})` invocation.
    agent_job: NotRequired[str]
    agent_outputs: Annotated[dict[str, str], merge_agent_outputs]
    final_answer: str
