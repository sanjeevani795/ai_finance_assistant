"""LangGraph-native fan-out: dynamic `Send` list from orchestration output."""

from __future__ import annotations

import logging

from langgraph.types import Send

from workflow.state import GraphState

logger = logging.getLogger(__name__)

SPECIALIST_NODE = "specialist"


def _dedupe_agents(raw: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for aid in raw:
        if aid not in seen:
            seen.add(aid)
            out.append(aid)
    return out


def route_specialists(state: GraphState) -> list[Send]:
    """Return one `Send` per specialist so LangGraph schedules them in parallel."""
    raw = (state.get("orchestration") or {}).get("agents") or ["finance_qa"]
    if not isinstance(raw, list):
        raw = ["finance_qa"]
    agents = _dedupe_agents([a for a in raw if isinstance(a, str)])
    if not agents:
        agents = ["finance_qa"]
    logger.info("LangGraph fan-out: %s parallel specialist task(s): %s", len(agents), agents)
    return [
        Send(
            SPECIALIST_NODE,
            {"agent_job": aid},
        )
        for aid in agents
    ]
