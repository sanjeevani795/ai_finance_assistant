"""Abstract base for all specialist agents (shared LLM invocation + message shape)."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import ClassVar

from agents.context import AgentContext
from core.openai_client import chat_text, get_client

logger = logging.getLogger(__name__)


def format_user_message(ctx: AgentContext, extra: str = "") -> str:
    parts = [
        f"Selected agent: {ctx.agent_id}",
        f"User question:\n{ctx.user_query.strip()}",
    ]
    if ctx.conversation_context.strip():
        parts.append(f"Conversation context:\n{ctx.conversation_context.strip()}")
    if ctx.rag_context.strip():
        parts.append(f"RAG context (retrieved knowledge base):\n{ctx.rag_context.strip()}")
    if ctx.market_context.strip():
        parts.append(f"Market data context:\n{ctx.market_context.strip()}")
    if ctx.user_profile_json.strip():
        parts.append(f"User profile (JSON):\n{ctx.user_profile_json.strip()}")
    if extra.strip():
        parts.append(f"Agent-specific structured context:\n{extra.strip()}")
    return "\n\n".join(parts)


class BaseAgent(ABC):
    """Common pattern: optional structured context + one OpenAI completion."""

    agent_id: ClassVar[str]

    @abstractmethod
    def system_instruction(self) -> str:
        """System prompt unique to this agent."""

    def extra_llm_blocks(self, ctx: AgentContext) -> str:
        """Optional factual block (math, RSS, etc.) appended before the LLM call."""
        return ""

    def run(self, ctx: AgentContext) -> str:
        client = get_client()
        extra = self.extra_llm_blocks(ctx)
        user = format_user_message(ctx, extra)
        try:
            return chat_text(
                client,
                cfg=ctx.cfg,
                system=self.system_instruction(),
                user=user,
                temperature=ctx.cfg.openai_temperature,
            )
        except Exception:
            logger.exception("Agent %s failed.", self.agent_id)
            return f"(Agent {self.agent_id} failed — please try again or rephrase your question.)"
