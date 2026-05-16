"""Build scoped `AgentContext` and invoke the correct specialist (graph entrypoint)."""

from __future__ import annotations

from typing import Any

from agents.context import AgentContext
from agents.registry import get_agent
from core.config import AppConfig


def scope_rag(agent_id: str, full_rag: str) -> str:
    """Only educational agents receive retrieved KB text (keeps other agents focused)."""
    if agent_id in {"finance_qa", "tax_education", "goal_planning"}:
        return full_rag
    return ""


def scope_market(agent_id: str, full_market: str) -> str:
    """Market prefetch is passed to market + portfolio agents."""
    if agent_id in {"market_analysis", "portfolio_analysis", "news_synthesizer"}:
        return full_market
    return ""


def build_agent_context(agent_id: str, state: dict[str, Any], cfg: AppConfig) -> AgentContext:
    return AgentContext(
        agent_id=agent_id,
        user_query=state.get("user_query") or "",
        conversation_context=state.get("conversation_context") or "",
        rag_context=scope_rag(agent_id, state.get("rag_context") or ""),
        market_context=scope_market(agent_id, state.get("market_context") or ""),
        user_profile_json=state.get("user_profile_json") or "",
        cfg=cfg,
    )


def invoke_agent(agent_id: str, state: dict[str, Any], cfg: AppConfig) -> str:
    ctx = build_agent_context(agent_id, state, cfg)
    return get_agent(agent_id).run(ctx)
