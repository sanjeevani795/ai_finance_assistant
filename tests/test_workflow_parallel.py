"""LangGraph Send fan-out + parallel specialist merge (mocked LLM layer)."""

from __future__ import annotations

from unittest.mock import MagicMock

from core.config import load_config
from workflow.graph import WorkflowDeps, build_graph


def test_parallel_specialists_merge_dict(monkeypatch) -> None:
    cfg = load_config()
    deps = WorkflowDeps(cfg=cfg, retriever=MagicMock(), market=MagicMock())
    deps.retriever.retrieve.return_value = ""
    deps.market.quotes_for_symbols.return_value = ""

    monkeypatch.setattr(
        "workflow.graph.orchestrate",
        lambda **kwargs: {
            "agents": ["finance_qa", "market_analysis", "tax_education"],
            "reason": "test",
            "raw": {},
        },
    )
    monkeypatch.setattr(
        "agents.facade.invoke_agent",
        lambda agent_id, state, cfg: f"OUT-{agent_id}",
    )

    def _synth(**kwargs):
        keys = ",".join(sorted(kwargs["agent_outputs"].keys()))
        return f"FINAL:{keys}"

    monkeypatch.setattr("workflow.graph.synthesize", _synth)

    app = build_graph(deps)
    cfgx = {"configurable": {"thread_id": "parallel-test"}}
    out = app.invoke(
        {"user_query": "q", "conversation_context": "", "user_profile_json": "{}"},
        cfgx,
    )
    keys = set(out["agent_outputs"]) - {"__reset__"}
    assert keys >= {"finance_qa", "market_analysis", "tax_education"}
    assert "FINAL:" in out["final_answer"]


def test_agent_outputs_reset_between_turns(monkeypatch) -> None:
    cfg = load_config()
    deps = WorkflowDeps(cfg=cfg, retriever=MagicMock(), market=MagicMock())
    deps.retriever.retrieve.return_value = ""
    deps.market.quotes_for_symbols.return_value = ""

    calls = {"n": 0}

    def _orch(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"agents": ["finance_qa"], "reason": "a", "raw": {}}
        return {"agents": ["market_analysis"], "reason": "b", "raw": {}}

    monkeypatch.setattr("workflow.graph.orchestrate", _orch)
    monkeypatch.setattr(
        "agents.facade.invoke_agent",
        lambda agent_id, state, cfg: f"X-{agent_id}",
    )
    monkeypatch.setattr("workflow.graph.synthesize", lambda **kwargs: "ok")

    app = build_graph(deps)
    cfgx = {"configurable": {"thread_id": "reset-test"}}
    app.invoke({"user_query": "one", "conversation_context": "", "user_profile_json": "{}"}, cfgx)
    out2 = app.invoke({"user_query": "two", "conversation_context": "", "user_profile_json": "{}"}, cfgx)
    outs = dict(out2["agent_outputs"])
    outs.pop("__reset__", None)
    assert "finance_qa" not in outs
    assert "market_analysis" in outs
