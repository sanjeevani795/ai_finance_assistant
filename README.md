---
title: AI Finance Assistant
emoji: 📈
colorFrom: blue
colorTo: green
sdk: gradio
app_file: src/web_app/gradio_app.py
pinned: false
---

# AI Finance Assistant

AI Finance Assistant is a multi-agent financial education application that combines:

- OpenAI chat completions for reasoning and response generation.
- LangGraph for orchestration and parallel specialist execution.
- FAISS + OpenAI embeddings for retrieval-augmented generation (RAG).
- yFinance and Alpha Vantage integrations for market context.
- Gradio for a lightweight interactive chat UI.

This project is intended for educational financial guidance, not personalized investment, legal, or tax advice.

## Architecture Overview

Detailed visual flow: 

<img width="1259" height="664" alt="image" src="https://github.com/user-attachments/assets/943233e3-27df-4567-8890-8e8dbce40b46" />


### High-level flow

1. User sends a message in the Gradio UI.
2. Workflow `prepare_context` stage:
- Retrieves relevant KB chunks from FAISS (if index exists).
- Extracts ticker symbols and prefetches market quote/trend context.
3. `orchestrate` stage:
- Orchestrator model selects a minimal set of specialist agents.
4. Parallel `specialist` stage:
- LangGraph fans out one job per selected specialist.
- Each specialist receives a scoped context payload.
5. `synthesize` stage:
- Final synthesizer merges specialist outputs into one response.
6. Response is returned to chat history with educational disclaimer behavior enforced by prompts.

### Core components

- `src/web_app/gradio_app.py`: UI entrypoint and graph invocation.
- `src/workflow/graph.py`: graph assembly and runtime node logic.
- `src/workflow/routing.py`: dynamic specialist fan-out via `Send`.
- `src/agents/orchestrator.py`: JSON routing decision (`agents`, `reason`).
- `src/agents/`: specialist implementations and shared base class.
- `src/rag/`: ingestion, FAISS persistence/loading, retrieval formatting.
- `src/data/`: market data adapters and aggregation layer.
- `src/core/`: config loading and OpenAI client wrappers.

### Specialist catalog

- `finance_qa`: general personal finance/investing education.
- `portfolio_analysis`: diversification/concentration analysis + deterministic portfolio math block.
- `market_analysis`: live market interpretation from prefetched market context.
- `goal_planning`: goal framing + deterministic savings projection block.
- `news_synthesizer`: RSS headline summarization and context.
- `tax_education`: tax concept education (non-personalized).

## Setup Instructions

### Prerequisites

- Python 3.11+
- `pip`
- OpenAI API key (`OPENAI_API_KEY`)
- Optional: Alpha Vantage key (`ALPHA_VANTAGE_API_KEY`)

### Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# set OPENAI_API_KEY and optional ALPHA_VANTAGE_API_KEY in .env
python scripts/build_demo_index.py
python run.py
```

Open the local Gradio URL shown in terminal (default `http://127.0.0.1:7860`).

### Docker setup

```bash
export OPENAI_API_KEY="sk-..."
docker compose up --build
```

For deployment patterns, runtime secret injection, ingest profile, and hardening, see [DEPLOYMENT.md](/Users/sanjeevanishrivastava/IK_Project1/ai_finance_assistant/DEPLOYMENT.md).


### Application entrypoints

- `python run.py`
- `web_app.gradio_app.launch()`
- `web_app.gradio_app.make_respond_fn()`

`respond(message, history, thread_id) -> (history, thread_id)`:

- Input:
- `message: str`
- `history: list[list[str | None]]`
- `thread_id: str`
- Behavior:
- Builds graph state (`user_query`, `conversation_context`, `user_profile_json`).
- Invokes LangGraph with checkpointer config (`thread_id`).
- Appends assistant response to chat history.

### Workflow state contract

`GraphState` keys in `src/workflow/state.py`:

- Inputs: `user_query`, `conversation_context`, `user_profile_json`
- Prepared context: `rag_context`, `market_context`
- Orchestration: `orchestration` (`agents`, `reason`, `raw`)
- Fan-out plumbing: `agent_job`, `agent_outputs`
- Final output: `final_answer`

### Agent interfaces

- Orchestrator:
- `orchestrate(user_query, conversation_context, cfg) -> dict`
- Output shape: `{ "agents": list[str], "reason": str, "raw": dict }`

- Specialist execution:
- `invoke_agent(agent_id, state, cfg) -> str`
- Shared payload contract via `AgentContext`:
- `agent_id`, `user_query`, `conversation_context`, `rag_context`, `market_context`, `user_profile_json`, `cfg`

- Synthesizer:
- `synthesize(user_query, conversation_context, orchestration, agent_outputs, rag_context, market_context, cfg) -> str`

### RAG interfaces

- `load_faiss(cfg) -> FAISS | None`
- `build_faiss_from_documents(documents, cfg) -> FAISS`
- `save_faiss(store, cfg) -> None`
- `FinanceRetriever.retrieve(query) -> str`

Retrieved context is formatted into numbered blocks with source metadata.

### Market data interfaces

- `MarketDataService.quote(symbol) -> dict`
- `MarketDataService.trend(symbol) -> dict`
- `MarketDataService.quotes_for_symbols(symbols) -> str`

Provider strategy:

- If `prefer_yfinance=true`, try yFinance first, then Alpha Vantage fallback (if key configured).
- If `prefer_yfinance=false`, try Alpha Vantage first, then yFinance fallback.

## Usage Examples

### 1) Educational finance question

Prompt:

`What is dollar-cost averaging and when is it useful?`

Expected route:

- Orchestrator usually selects `finance_qa`.
- If KB index exists, RAG snippets enrich terminology and explanation depth.

### 2) Market + portfolio prompt

Prompt:

`summarize best practices for emergency fund sizing?`

Expected route:

- `portfolio_analysis` for concentration math.
- `market_analysis` for current quote/trend context.
- Synthesizer merges both views into one answer.

### 3) Goal planning prompt

Prompt:

`I want $50,000 in 5 years and can save $600/month. Am I on track?`

Expected route:

- `goal_planning` includes deterministic projection snippets from parsed numbers.
- Final response explains assumptions and missing inputs.

### 4) News summary prompt

Prompt:

`What are the major market headlines today?`

Expected route:

- `news_synthesizer` fetches configured RSS titles.
- Response summarizes fetched headlines and caveats feed latency.

## Troubleshooting Guide

### `OPENAI_API_KEY is not set`

Cause:

- Missing env var at runtime.

Fix:

- Set `OPENAI_API_KEY` in your shell or `.env`.
- Re-run `python run.py` or `docker compose up --build`.

### App starts but RAG answers are empty

Cause:

- FAISS files missing at `data/faiss_index/<name>.faiss` and `.pkl`.

Fix:

- Run `python scripts/build_demo_index.py`.
- Confirm `config.yaml` path settings match the generated index location.

### Market data errors for ticker queries

Cause:

- Invalid ticker, provider outage, rate limit, or network restrictions.

Fix:

- Validate symbol format.
- Add `ALPHA_VANTAGE_API_KEY` for fallback path.
- Retry after cooldown if free-tier throttled.

### RSS/news responses say no headlines fetched

Cause:

- Feed unavailable, blocked egress, or XML parse failure.

Fix:

- Check outbound network access.
- Verify URLs in `config.yaml` under `news.rss_urls`.
- Increase `news.request_timeout_seconds` if needed.

### Docker container exits quickly

Cause:

- Missing runtime key injection.

Fix:

- Ensure `OPENAI_API_KEY` is exported before `docker compose up --build`.
- See [DEPLOYMENT.md](/Users/sanjeevanishrivastava/IK_Project1/ai_finance_assistant/DEPLOYMENT.md) for runtime secret patterns.

## Testing

Run tests with:

```bash
pytest -q
```

Test suite includes coverage for config loading, symbol extraction, portfolio/goal deterministic helpers, workflow parallel fan-out behavior, and selected agent utilities.

## Project Structure

- `src/agents/`: orchestrator, specialists, prompts, deterministic helpers.
- `src/workflow/`: graph, routing, state reducers.
- `src/rag/`: ingestion, FAISS lifecycle, retrieval wrapper.
- `src/data/`: market provider clients and service layer.
- `src/web_app/`: Gradio UI wiring.
- `scripts/`: index build and container entrypoint scripts.
- `tests/`: unit/integration-style behavior tests.
