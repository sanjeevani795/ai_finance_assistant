"""Portfolio analysis — combines narrative guidance with deterministic weight / concentration math."""

from __future__ import annotations

from typing import ClassVar

from agents.base import BaseAgent
from agents.context import AgentContext
from agents.portfolio_math import portfolio_summary_block


class PortfolioAnalysisAgent(BaseAgent):
    agent_id: ClassVar[str] = "portfolio_analysis"

    def system_instruction(self) -> str:
        return (
            "You are the Portfolio Analysis specialist. Educational only — not personalized investment advice.\n\n"
            "Interpret the structured weight/concentration block when present. Explain diversification, "
            "concentration risk, and what additional data (covariance, time horizon, liquidity) would be needed "
            "for a fuller analysis. If the user did not supply weights, ask for holdings or target allocation."
        )

    def extra_llm_blocks(self, ctx: AgentContext) -> str:
        return portfolio_summary_block(ctx.user_query)
