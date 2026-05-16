"""Market analysis — interprets prefetched live quotes and simple trend summaries."""

from __future__ import annotations

from typing import ClassVar

from agents.base import BaseAgent


class MarketAnalysisAgent(BaseAgent):
    agent_id: ClassVar[str] = "market_analysis"

    def system_instruction(self) -> str:
        return (
            "You are the Market Analysis specialist. Use only numbers that appear in the Market data context. "
            "Do not fabricate prices or volumes. Explain moves cautiously (many drivers); avoid firm predictions. "
            "Clarify that delayed/unofficial vendor data may differ from a broker's live tape."
        )
