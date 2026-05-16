"""Registry of concrete specialist agents."""

from __future__ import annotations

from agents.base import BaseAgent
from agents.finance_qa import FinanceQAAgent
from agents.goal_planning import GoalPlanningAgent
from agents.market_analysis import MarketAnalysisAgent
from agents.news_synthesizer import NewsSynthesizerAgent
from agents.portfolio_analysis import PortfolioAnalysisAgent
from agents.tax_education import TaxEducationAgent

_REGISTRY: dict[str, BaseAgent] = {
    FinanceQAAgent.agent_id: FinanceQAAgent(),
    PortfolioAnalysisAgent.agent_id: PortfolioAnalysisAgent(),
    MarketAnalysisAgent.agent_id: MarketAnalysisAgent(),
    GoalPlanningAgent.agent_id: GoalPlanningAgent(),
    NewsSynthesizerAgent.agent_id: NewsSynthesizerAgent(),
    TaxEducationAgent.agent_id: TaxEducationAgent(),
}

_DEFAULT = _REGISTRY[FinanceQAAgent.agent_id]


def get_agent(agent_id: str) -> BaseAgent:
    return _REGISTRY.get(agent_id) or _DEFAULT
