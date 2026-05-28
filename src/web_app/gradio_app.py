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
from rag.faiss_store import build_faiss_from_documents, load_faiss, save_faiss
from rag.ingest import chunk_documents, load_text_file
from rag.retriever import FinanceRetriever
from utils.logging_config import setup_logging
from utils.scope_guard import OUT_OF_SCOPE_REPLY, is_finance_or_specialist_scope
from workflow.graph import WorkflowDeps, build_graph, default_user_profile_json

logger = logging.getLogger(__name__)


def _format_history_for_graph(history: list[dict[str, str]]) -> str:
    """Gradio Chatbot history in messages format."""
    if not history:
        return ""
    lines: list[str] = []
    for msg in history[-16:]:
        role = str(msg.get("role") or "").strip().lower()
        content = str(msg.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            lines.append(f"User: {content}")
        elif role == "assistant":
            lines.append(f"Assistant: {content}")
    return "\n".join(lines)


def _normalize_ui_history_to_messages(history: object) -> list[dict[str, str]]:
    if not history:
        return []
    messages: list[dict[str, str]] = []
    for item in history:  # type: ignore[assignment]
        if isinstance(item, dict):
            role = str(item.get("role") or "").strip().lower()
            content = str(item.get("content") or "")
            if role in {"user", "assistant"}:
                messages.append({"role": role, "content": content})
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            user_text = "" if item[0] is None else str(item[0])
            assistant_text = "" if item[1] is None else str(item[1])
            if user_text:
                messages.append({"role": "user", "content": user_text})
            if assistant_text:
                messages.append({"role": "assistant", "content": assistant_text})
    return messages


def _messages_to_legacy_pairs(messages: list[dict[str, str]]) -> list[list[str | None]]:
    pairs: list[list[str | None]] = []
    pending_user: str | None = None
    for msg in messages:
        role = str(msg.get("role") or "").strip().lower()
        content = str(msg.get("content") or "")
        if role == "user":
            if pending_user is not None:
                pairs.append([pending_user, None])
            pending_user = content
        elif role == "assistant":
            if pending_user is None:
                pairs.append(["", content])
            else:
                pairs.append([pending_user, content])
                pending_user = None
    if pending_user is not None:
        pairs.append([pending_user, None])
    return pairs


def _to_ui_history(messages: list[dict[str, str]], messages_mode: bool) -> object:
    sanitized: list[dict[str, str]] = []
    for m in messages:
        role = str(m.get("role") or "").strip().lower()
        if role not in {"user", "assistant"}:
            continue
        sanitized.append({"role": role, "content": str(m.get("content") or "")})
    if messages_mode:
        return sanitized
    print("log samitized value check : " , sanitized)
    return _messages_to_legacy_pairs(sanitized)


def _bool_env(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _maybe_build_faiss_if_missing(cfg) -> None:
    if not _bool_env("AUTO_BUILD_FAISS_ON_STARTUP", default=False):
        return
    sample = _ROOT / "data" / "sample_kb.txt"
    raw_docs_dir = cfg.raw_docs_dir
    docs = []
    if sample.is_file():
        docs.extend(
            load_text_file(
                sample,
                source_url="internal://sample_kb",
                category="Personal Finance / Investing",
            )
        )
    if raw_docs_dir.is_dir():
        for pattern in ("*.txt", "*.md"):
            for p in sorted(raw_docs_dir.rglob(pattern)):
                docs.extend(
                    load_text_file(
                        p,
                        source_url=f"internal://raw_docs/{p.relative_to(raw_docs_dir)}",
                        category="User Docs",
                    )
                )
    if not docs:
        logger.info("AUTO_BUILD_FAISS_ON_STARTUP=true but no source docs found; skipping FAISS build.")
        return
    logger.info("Building FAISS index on startup into %s", cfg.faiss_index_dir)
    chunks = chunk_documents(docs, cfg)
    store = build_faiss_from_documents(chunks, cfg)
    save_faiss(store, cfg)
    logger.info("FAISS index build complete.")


def make_respond_fn(*, messages_mode: bool):
    cfg = load_config()
    setup_logging(cfg.logs_dir)
    require_openai_key()
    av_key = alpha_vantage_key()
    logger.info("Alpha Vantage key detected: %s", "yes" if av_key else "no")

    store = load_faiss(cfg)
    if store is None:
        _maybe_build_faiss_if_missing(cfg)
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
        history: object,
        thread_id: str,
    ) -> Generator[tuple[object, str], None, None]:
        messages = _normalize_ui_history_to_messages(history)
        message = (message or "").strip()
        if not message:
            yield _to_ui_history(messages, messages_mode), thread_id
            return
        if not is_finance_or_specialist_scope(message):
            messages.append({"role": "user", "content": message})
            messages.append({"role": "assistant", "content": OUT_OF_SCOPE_REPLY})
            yield _to_ui_history(messages, messages_mode), thread_id
            return

        convo = _format_history_for_graph(messages)
        state = {
            "user_query": message,
            "conversation_context": convo,
            "user_profile_json": profile_json,
        }
        config = {"configurable": {"thread_id": thread_id or "default"}}

        status = "Processing your request...\n"
        messages.append({"role": "user", "content": message})
        messages.append({"role": "assistant", "content": status})
        yield _to_ui_history(messages, messages_mode), thread_id

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
                    messages[-1]["content"] = status
                    yield _to_ui_history(messages, messages_mode), thread_id
            answer = final_answer or "No response generated."
        except Exception as exc:  # noqa: BLE001
            logger.exception("Graph invoke failed.")
            answer = (
                "Something went wrong while processing your request. "
                f"Details have been logged. ({type(exc).__name__}: {exc})"
            )

        messages[-1]["content"] = ""
        yield _to_ui_history(messages, messages_mode), thread_id

        # Stream final text to UI in chunks for a progressive chat experience.
        chunk_size = 28
        built = ""
        for i in range(0, len(answer), chunk_size):
            built += answer[i : i + chunk_size]
            messages[-1]["content"] = built
            yield _to_ui_history(messages, messages_mode), thread_id
            time.sleep(0.01)

    return respond


def launch() -> None:
    with gr.Blocks(title="AI Finance Assistant") as demo:
        gr.Markdown(
            "## AI Finance Assistant\n"
            "Ask a question in natural language. The workflow routes your query to specialist agents, "
            "retrieves knowledge when available, and may fetch live market data for tickers (e.g. AAPL).\n\n"
            "**Educational use only** — not personalized financial or tax advice."
        )
        thread = gr.State(str(uuid.uuid4()))
        chat_kwargs = {"label": "Conversation", "height": 480}
        try:
            chat = gr.Chatbot(type="messages", **chat_kwargs)
        except TypeError:
            chat = gr.Chatbot(**chat_kwargs)
        messages_mode = str(getattr(chat, "type", "")).strip().lower() == "messages"
        respond = make_respond_fn(messages_mode=messages_mode)
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
        new_session.click(
            lambda: (_to_ui_history([], messages_mode), str(uuid.uuid4())),
            outputs=[chat, thread],
        )

    host = os.getenv("GRADIO_SERVER_NAME", "127.0.0.1")
    port = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    demo.queue().launch(server_name=host, server_port=port)


if __name__ == "__main__":
    launch()
