from unittest.mock import patch

from agents.context import AgentContext
from agents.news_synthesizer import NewsSynthesizerAgent
from core.config import load_config


def _ctx(market_context: str = "") -> AgentContext:
    return AgentContext(
        agent_id="news_synthesizer",
        user_query="What are the headlines about Nvidia?",
        conversation_context="",
        rag_context="",
        market_context=market_context,
        user_profile_json="{}",
        cfg=load_config(),
    )


def test_news_agent_uses_rss_when_available() -> None:
    agent = NewsSynthesizerAgent()
    with patch("agents.news_synthesizer.news_context_block", return_value="Recent headlines:\n- A"):
        block = agent.extra_llm_blocks(_ctx("NVDA: last=1"))
    assert block.startswith("Recent headlines:")


def test_news_agent_falls_back_to_market_context_when_rss_unavailable() -> None:
    agent = NewsSynthesizerAgent()
    with patch("agents.news_synthesizer.news_context_block", return_value=""):
        block = agent.extra_llm_blocks(_ctx("NVDA: last=123.45 source=yfinance"))
    assert "RSS headlines could not be fetched right now" in block
    assert "Market fallback context" in block
    assert "NVDA: last=123.45" in block
