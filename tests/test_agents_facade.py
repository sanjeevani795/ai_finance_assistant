"""Scoped context + registry wiring (inter-agent handoff is orchestrator → parallel agents → synthesize)."""

from __future__ import annotations

from agents.facade import build_agent_context, invoke_agent, scope_market, scope_rag
from agents.registry import get_agent
from core.config import load_config


def test_scope_rag_only_educational_agents() -> None:
    rag = "some kb text"
    assert scope_rag("finance_qa", rag) == rag
    assert scope_rag("tax_education", rag) == rag
    assert scope_rag("goal_planning", rag) == rag
    assert scope_rag("market_analysis", rag) == ""


def test_scope_market_for_market_and_portfolio() -> None:
    m = "AAPL last=1"
    assert scope_market("market_analysis", m) == m
    assert scope_market("portfolio_analysis", m) == m
    assert scope_market("finance_qa", m) == ""


def test_registry_returns_distinct_agents() -> None:
    assert get_agent("finance_qa") is not get_agent("market_analysis")


def test_invoke_agent_uses_registry(monkeypatch) -> None:
    cfg = load_config()
    state = {
        "user_query": "hi",
        "conversation_context": "",
        "rag_context": "RAGTEXT",
        "market_context": "MKT",
        "user_profile_json": "{}",
    }

    class Stub:
        agent_id = "finance_qa"

        def run(self, ctx):
            return f"seen_rag={bool(ctx.rag_context)}"

    monkeypatch.setattr("agents.facade.get_agent", lambda _aid: Stub())
    out = invoke_agent("finance_qa", state, cfg)
    assert "seen_rag=True" in out


def test_build_agent_context_scoping() -> None:
    cfg = load_config()
    ctx = build_agent_context(
        "market_analysis",
        {
            "user_query": "q",
            "conversation_context": "",
            "rag_context": "R",
            "market_context": "M",
            "user_profile_json": "{}",
        },
        cfg,
    )
    assert ctx.rag_context == ""
    assert ctx.market_context == "M"
