"""LangGraph workflow: prepare → orchestrate → parallel specialists (`Send`) → synthesize."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agents.facade import invoke_agent
from agents.orchestrator import orchestrate
from agents.specialists import synthesize
from core.config import AppConfig
from data.market_service import MarketDataService
from data.schemas import UserProfile
from rag.retriever import FinanceRetriever
from utils.symbols import query_mentions_market
from workflow.reducers import RESET_AGENT_OUTPUTS
from workflow.routing import SPECIALIST_NODE, route_specialists
from workflow.state import GraphState

logger = logging.getLogger(__name__)


@dataclass
class WorkflowDeps:
    cfg: AppConfig
    retriever: FinanceRetriever
    market: MarketDataService


def build_graph(deps: WorkflowDeps):
    def prepare_context(state: GraphState) -> dict:
        q = (state.get("user_query") or "").strip()
        rag_text = ""
        market_text = ""
        try:
            rag_text = deps.retriever.retrieve(q)
        except Exception:
            logger.exception("RAG retrieve failed during prepare_context.")
        try:
            if query_mentions_market(q):
                syms = deps.market.resolve_symbols_from_query(q)
                if syms:
                    market_text = deps.market.quotes_for_symbols(syms)
        except Exception:
            logger.exception("Market prefetch failed during prepare_context.")
        # Clear prior-turn specialist results when using a persistent checkpointer.
        return {
            "rag_context": rag_text,
            "market_context": market_text,
            "agent_outputs": {RESET_AGENT_OUTPUTS: ""},
        }

    def orchestrate_node(state: GraphState) -> dict:
        orch = orchestrate(
            user_query=state.get("user_query") or "",
            conversation_context=state.get("conversation_context") or "",
            cfg=deps.cfg,
        )
        return {"orchestration": orch}

    def specialist_node(state: GraphState) -> dict:
        agent_id = (state.get("agent_job") or "").strip() or "finance_qa"
        text = invoke_agent(agent_id, dict(state), deps.cfg)
        return {"agent_outputs": {agent_id: text}}

    def synthesize_node(state: GraphState) -> dict:
        raw_outputs = dict(state.get("agent_outputs") or {})
        raw_outputs.pop(RESET_AGENT_OUTPUTS, None)
        text = synthesize(
            user_query=state.get("user_query") or "",
            conversation_context=state.get("conversation_context") or "",
            orchestration=state.get("orchestration") or {},
            agent_outputs=raw_outputs,
            rag_context=state.get("rag_context") or "",
            market_context=state.get("market_context") or "",
            cfg=deps.cfg,
        )
        return {"final_answer": text}

    g = StateGraph(GraphState)
    g.add_node("prepare_context", prepare_context)
    g.add_node("orchestrate", orchestrate_node)
    g.add_node(SPECIALIST_NODE, specialist_node)
    g.add_node("synthesize", synthesize_node)

    g.add_edge(START, "prepare_context")
    g.add_edge("prepare_context", "orchestrate")
    g.add_conditional_edges("orchestrate", route_specialists)
    g.add_edge(SPECIALIST_NODE, "synthesize")
    g.add_edge("synthesize", END)

    memory = MemorySaver()
    return g.compile(checkpointer=memory)


def default_user_profile_json() -> str:
    return UserProfile().model_dump_json()
