"""News synthesizer — fetches RSS headlines then contextualizes (no invented stories)."""

from __future__ import annotations

from typing import ClassVar

from agents.base import BaseAgent
from agents.context import AgentContext
from agents.news_tools import news_context_block


class NewsSynthesizerAgent(BaseAgent):
    agent_id: ClassVar[str] = "news_synthesizer"

    def system_instruction(self) -> str:
        return (
            "You are the News Synthesizer specialist. Summarize and contextualize the supplied headlines only. "
            "If no headlines were fetched, say so and give a framework for reading financial news critically "
            "(sources, incentives, market vs. economy). Never invent quotes or URLs."
        )

    def extra_llm_blocks(self, ctx: AgentContext) -> str:
        return news_context_block(
            rss_urls=list(ctx.cfg.news_rss_urls),
            timeout=ctx.cfg.news_request_timeout_seconds,
            max_items_per_feed=ctx.cfg.news_max_items_per_feed,
        )
