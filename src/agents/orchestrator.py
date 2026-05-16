"""Route user queries to specialist agent ids."""

from __future__ import annotations

import logging
from typing import Any

from core.config import AppConfig
from core.openai_client import chat_json, get_client

from agents.prompts import ORCHESTRATOR_SYSTEM

logger = logging.getLogger(__name__)

VALID_AGENTS = frozenset(
    {
        "finance_qa",
        "portfolio_analysis",
        "market_analysis",
        "goal_planning",
        "news_synthesizer",
        "tax_education",
    }
)


def orchestrate(
    *,
    user_query: str,
    conversation_context: str,
    cfg: AppConfig,
) -> dict[str, Any]:
    client = get_client()
    system = ORCHESTRATOR_SYSTEM.format(max_agents=cfg.max_agents_per_query)
    user_parts = [f"User message:\n{user_query.strip()}"]
    if conversation_context.strip():
        user_parts.append(f"Prior conversation (condensed):\n{conversation_context.strip()}")
    payload = chat_json(
        client,
        cfg=cfg,
        system=system,
        user="\n\n".join(user_parts),
        temperature=0.0,
    )
    raw_agents = payload.get("agents") or []
    if not isinstance(raw_agents, list):
        raw_agents = []
    agents = [a for a in raw_agents if isinstance(a, str) and a in VALID_AGENTS]
    if not agents:
        logger.warning("Orchestrator returned no valid agents; defaulting to finance_qa. Payload=%s", payload)
        agents = ["finance_qa"]
    agents = agents[: cfg.max_agents_per_query]
    reason = str(payload.get("reason") or "").strip()
    return {"agents": agents, "reason": reason, "raw": payload}
