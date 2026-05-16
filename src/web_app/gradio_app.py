"""Gradio UI: single prompt in, assistant answer out (Claude-style)."""

from __future__ import annotations

import logging
import os
import sys
import time
import uuid
from collections.abc import Generator
from pathlib import Path

# Ensure `src/` is on sys.path when launched as a script.
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import gradio as gr

from core.config import alpha_vantage_key, load_config, require_openai_key
from data.market_service import MarketDataService
from rag.faiss_store import load_faiss
from rag.retriever import FinanceRetriever
from utils.logging_config import setup_logging
from utils.scope_guard import OUT_OF_SCOPE_REPLY, is_finance_or_specialist_scope
from workflow.graph import WorkflowDeps, build_graph, default_user_profile_json

logger = logging.getLogger(__name__)


def _format_history_for_graph(history: list[list[str | None]]) -> str:
    """Gradio Chatbot history: list of [user, assistant]."""
    if not history:
        return ""
    lines: list[str] = []
    for turn in history[-8:]:
        u, a = turn[0] or "", turn[1] or ""
        if u.strip():
            lines.append(f"User: {u.strip()}")
        if a.strip():
            lines.append(f"Assistant: {a.strip()}")
    return "\n".join(lines)


def make_respond_fn():
    cfg = load_config()
    setup_logging(cfg.logs_dir)
    require_openai_key()
    av_key = alpha_vantage_key()
    logger.info("Alpha Vantage key detected: %s", "yes" if av_key else "no")

    store = load_faiss(cfg)
    retriever = FinanceRetriever(cfg, store)
    market = MarketDataService(cfg)
    deps = WorkflowDeps(cfg=cfg, retriever=retriever, market=market)
    graph = build_graph(deps)
    profile_json = default_user_profile_json()

    def _status_lines_from_event(event: dict) -> list[str]:
        lines: list[str] = []
        for node, payload in event.items():
            if node == "prepare_context":
                rag = bool((payload or {}).get("rag_context"))
                mkt = bool((payload or {}).get("market_context"))
                lines.append(f"- Prepared context (RAG={'yes' if rag else 'no'}, Market={'yes' if mkt else 'no'})")
            elif node == "orchestrate":
                agents = ((payload or {}).get("orchestration") or {}).get("agents") or []
                if isinstance(agents, list) and agents:
                    lines.append(f"- Routed to specialists: {', '.join(str(a) for a in agents)}")
            elif node == "specialist":
                outs = (payload or {}).get("agent_outputs") or {}
                for aid in outs:
                    if aid.startswith("__"):
                        continue
                    lines.append(f"- Completed specialist: {aid}")
            elif node == "synthesize":
                lines.append("- Synthesizing final response...")
        return lines

    def respond(
        message: str,
        history: list[list[str | None]],
        thread_id: str,
    ) -> Generator[tuple[list[list[str | None]], str], None, None]:
        message = (message or "").strip()
        if not message:
            yield history, thread_id
            return
        if not is_finance_or_specialist_scope(message):
            history = history or []
            history.append([message, OUT_OF_SCOPE_REPLY])
            yield history, thread_id
            return

        convo = _format_history_for_graph(history)
        state = {
            "user_query": message,
            "conversation_context": convo,
            "user_profile_json": profile_json,
        }
        config = {"configurable": {"thread_id": thread_id or "default"}}

        history = history or []
        status = "Processing your request...\n"
        history.append([message, status])
        yield history, thread_id

        try:
            final_answer = ""
            for event in graph.stream(state, config=config, stream_mode="updates"):
                synth = (event or {}).get("synthesize") or {}
                if isinstance(synth, dict):
                    candidate = str(synth.get("final_answer") or "").strip()
                    if candidate:
                        final_answer = candidate
                new_lines = _status_lines_from_event(event)
                if new_lines:
                    status = status + "\n".join(new_lines) + "\n"
                    history[-1][1] = status
                    yield history, thread_id
            answer = final_answer or "No response generated."
        except Exception as exc:  # noqa: BLE001
            logger.exception("Graph invoke failed.")
            answer = (
                "Something went wrong while processing your request. "
                f"Details have been logged. ({type(exc).__name__}: {exc})"
            )

        history[-1][1] = ""
        yield history, thread_id

        # Stream final text to UI in chunks for a progressive chat experience.
        chunk_size = 28
        built = ""
        for i in range(0, len(answer), chunk_size):
            built += answer[i : i + chunk_size]
            history[-1][1] = built
            yield history, thread_id
            time.sleep(0.01)

    return respond


def launch() -> None:
    respond = make_respond_fn()

    with gr.Blocks(title="AI Finance Assistant") as demo:
        gr.Markdown(
            "## AI Finance Assistant\n"
            "Ask a question in natural language. The workflow routes your query to specialist agents, "
            "retrieves knowledge when available, and may fetch live market data for tickers (e.g. AAPL).\n\n"
            "**Educational use only** — not personalized financial or tax advice."
        )
        thread = gr.State(str(uuid.uuid4()))
        chat = gr.Chatbot(label="Conversation", height=480)
        msg = gr.Textbox(
            label="Your message",
            placeholder="e.g. What is dollar-cost averaging?  Or: What is AAPL trading at?",
            lines=3,
        )
        with gr.Row():
            send = gr.Button("Send", variant="primary")
            new_session = gr.Button("New session")

        send.click(respond, inputs=[msg, chat, thread], outputs=[chat, thread]).then(
            lambda: "", outputs=msg
        )
        new_session.click(lambda: ([], str(uuid.uuid4())), outputs=[chat, thread])

    host = os.getenv("GRADIO_SERVER_NAME", "127.0.0.1")
    port = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    demo.queue().launch(server_name=host, server_port=port)


if __name__ == "__main__":
    launch()
