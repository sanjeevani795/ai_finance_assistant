"""Final response synthesis (merges parallel specialist outputs)."""

from __future__ import annotations

import logging

from core.config import AppConfig
from core.openai_client import chat_text, get_client

from agents.prompts import SYNTHESIZER_SYSTEM

logger = logging.getLogger(__name__)


def synthesize(
    *,
    user_query: str,
    conversation_context: str,
    orchestration: dict,
    agent_outputs: dict[str, str],
    rag_context: str,
    market_context: str,
    cfg: AppConfig,
) -> str:
    client = get_client()
    lines = [
        f"User question:\n{user_query.strip()}",
    ]
    if conversation_context.strip():
        lines.append(f"Conversation context:\n{conversation_context.strip()}")
    if orchestration:
        lines.append(f"Orchestration:\n{orchestration}")
    if rag_context.strip():
        lines.append(f"RAG context:\n{rag_context.strip()}")
    if market_context.strip():
        lines.append(f"Market context:\n{market_context.strip()}")
    lines.append("Specialist outputs:")
    for k, v in agent_outputs.items():
        if k.startswith("__"):
            continue
        lines.append(f"--- {k} ---\n{v.strip()}")
    user = "\n\n".join(lines)
    try:
        return chat_text(
            client,
            cfg=cfg,
            system=SYNTHESIZER_SYSTEM,
            user=user,
            temperature=cfg.openai_temperature,
        )
    except Exception:
        logger.exception("Synthesize failed.")
        return "The assistant could not merge specialist responses. Please try again."
