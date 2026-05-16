# Technical Design Document

## 1. System Architecture Decisions

### 1.1 Architectural style

The system uses a Langgraph-based, multi-agent orchestration pattern:

- A central orchestration step classifies user intent.
- Specialists execute in parallel with scoped context.
- A final synthesizer merges outputs into a single user-facing response.

This design provides:

- Separation of concerns by domain (market, goals, portfolio, tax, news, general QA).
- Prompt precision through narrower agent responsibilities.
- Extensibility for adding/removing specialists without redesigning the full pipeline.

### 1.2 Workflow runtime

LangGraph is used as the execution engine:

- Deterministic node topology (`prepare_context -> orchestrate -> specialist* -> synthesize`).
- Native dynamic fan-out via `Send` for parallel specialist jobs.
- Checkpointing through `MemorySaver` and thread identifiers to preserve conversation continuity.

### 1.3 Data-source strategy

The architecture separates retrieval and live data concerns:

- RAG source: local FAISS index built from project KB text/documents.
- Live market source: yFinance primary (configurable) with Alpha Vantage fallback.
- News source: lightweight RSS fetch through stdlib tooling.

Benefits:

- High availability from multi-provider market fallback.
- Low-latency local vector search.
- Minimal deployment footprint for news ingestion.

### 1.4 Configuration and environment

`AppConfig` unifies runtime configuration from YAML and environment variables:

- Model/config knobs live in `config.yaml`.
- Secrets (`OPENAI_API_KEY`, optional `ALPHA_VANTAGE_API_KEY`) are runtime-only env vars.

This keeps environments reproducible while avoiding secret leakage into images/repo.

## 2. Agent Communication Protocols

### 2.1 Message contracts

All specialist agents consume a shared immutable `AgentContext` object containing:

- `agent_id`
- `user_query`
- `conversation_context`
- `rag_context`
- `market_context`
- `user_profile_json`
- `cfg`

The orchestrator produces JSON with:

- `agents: list[str]`
- `reason: str`
- `raw: dict`

The synthesizer receives:

- Original user question and conversation context.
- Orchestration payload.
- `agent_outputs` map keyed by specialist id.
- Prepared contexts (`rag_context`, `market_context`).

### 2.2 Context scoping protocol

To reduce irrelevant context bleed, the facade enforces scoped context propagation:

- RAG context is passed only to: `finance_qa`, `tax_education`, `goal_planning`.
- Market context is passed only to: `market_analysis`, `portfolio_analysis`.

Protocol outcome:

- Lower prompt noise and token pressure.
- Lower chance of inappropriate grounding (for example, tax agent overusing market snippets).

### 2.3 Parallel output merge protocol

Specialist outputs are merged through a reducer:

- `agent_outputs` is a dictionary merged by `merge_agent_outputs`.
- A sentinel `__reset__` key clears stale results when a new turn starts with checkpoint memory.

This protocol ensures deterministic aggregation even when parallel tasks return in variable order.

### 2.4 Failure-handling protocol

- Orchestrator failure or invalid output defaults to `finance_qa`.
- Specialist failures return a bounded fallback message instead of raising.
- Synthesis failure returns a safe retry prompt.
- Retrieval/provider failures degrade gracefully by returning empty context blocks.

The UX remains responsive without exposing stack traces to end users.

## 3. RAG Implementation Details

### 3.1 Ingestion pipeline

RAG ingestion path:

1. Load source documents (`TextLoader` or string-backed records).
2. Attach metadata (`source_file`, optional `source_url`, optional `category`).
3. Chunk documents via `RecursiveCharacterTextSplitter`.
4. Embed chunks using `OpenAIEmbeddings` (`text-embedding-3-large` by default).
5. Build and persist FAISS index (`.faiss` + `.pkl`).

Chunking defaults:

- `chunk_size = 900`
- `chunk_overlap = 120`

### 3.2 Retrieval pipeline

At query time:

1. `FinanceRetriever.retrieve(query)` runs similarity search (`k = rag_retrieval_k`, default 6).
2. Results are formatted as numbered blocks.
3. Each block includes source metadata where available (`source_url` / `source_file`, category).
4. Combined retrieval text is injected into eligible specialist prompts.

If FAISS files are absent or retrieval errors occur, the pipeline returns an empty context string and proceeds.

### 3.3 Citation and traceability model

The retrieval formatter preserves metadata in-line, enabling model-accessible provenance:

- `source=<url_or_file>`
- `category=<tag>`

This creates traceability hooks for future UI citation rendering without changing retrieval internals.

### 3.4 Storage model

- Default index location: `data/faiss_index/finance_kb.*`
- Optional `manifest.pkl` supports ingest/source bookkeeping.

Local-disk storage favors simple deployment and deterministic startup behavior.

## 4. Performance Considerations

### 4.1 Latency contributors

Primary latency components:

- Orchestrator model call.
- Parallel specialist model calls (critical path is slowest specialist, not sum).
- Synthesizer model call.
- Optional external I/O (yFinance, Alpha Vantage, RSS) and vector search.

### 4.2 Throughput and efficiency techniques

Implemented optimizations:

- Parallel specialist execution with LangGraph `Send`.
- TTL caching for market data and trend lookups.
- Retry with backoff for flaky provider calls.
- Alpha Vantage soft-throttle guard (free-tier aware).
- Context scoping to reduce prompt tokens per specialist.
- Lightweight retrieval formatting to avoid oversized prompt blocks.

### 4.3 Reliability vs speed tradeoffs

- Retrieval failures return empty context to maintain response availability.
- Provider fallback improves reliability at the cost of occasional extra latency.
- Max specialists per query (`workflow.max_agents_per_query`, default 4) caps fan-out cost.

### 4.4 Resource considerations

- Embedding/index generation is the most expensive offline operation.
- Runtime memory grows with loaded FAISS index size and LangGraph state snapshots.
- Deployment should set CPU/memory limits, and optionally persist FAISS/log directories on volumes.

## 5. Known Constraints

- No first-class REST API yet; current interface is Gradio UI and Python entrypoints.
- RSS feeds can be delayed/unavailable and are not guaranteed real-time.
- yFinance is unofficial data; broker/live-feed parity is not guaranteed.
- Citation rendering is prompt-level today, not structured UI output.

