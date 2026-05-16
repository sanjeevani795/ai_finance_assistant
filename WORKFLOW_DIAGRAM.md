# Workflow Diagram

This document shows how a user prompt moves through the system from input to final answer.

## End-to-End Flow

```mermaid
flowchart TD
    A[User enters prompt in Gradio UI] --> B[gradio_app.respond]
    B --> C[Build GraphState<br/>user_query, conversation_context, user_profile_json]
    C --> D[LangGraph: prepare_context]

    D --> D1[RAG retrieve from FAISS<br/>FinanceRetriever.retrieve]
    D --> D2[Market prefetch when market intent detected<br/>resolve_symbols_from_query + quotes_for_symbols]
    D1 --> E[Update state.rag_context]
    D2 --> F[Update state.market_context]
    E --> G[LangGraph: orchestrate]
    F --> G

    G --> G1[Orchestrator LLM returns JSON:<br/>agents + reason]
    G1 --> H[route_specialists creates Send jobs]

    H --> I1[Specialist: finance_qa]
    H --> I2[Specialist: portfolio_analysis]
    H --> I3[Specialist: market_analysis]
    H --> I4[Specialist: goal_planning]
    H --> I5[Specialist: news_synthesizer]
    H --> I6[Specialist: tax_education]

    I1 --> J[merge_agent_outputs reducer]
    I2 --> J
    I3 --> J
    I4 --> J
    I5 --> J
    I6 --> J

    J --> K[LangGraph: synthesize]
    K --> K1[Synthesizer LLM merges specialist outputs]
    K1 --> L[state.final_answer]
    L --> M[Gradio streams status + final text chunks]
    M --> N[User sees final response]
```

## Sequence View

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Gradio UI
    participant G as LangGraph
    participant R as RAG Retriever
    participant MD as MarketDataService
    participant O as Orchestrator LLM
    participant S as Specialist Agents
    participant Y as Synthesizer LLM

    U->>UI: Prompt
    UI->>G: invoke stream with GraphState
    G->>R: retrieve(query)
    R-->>G: rag_context
    G->>MD: resolve symbols + quotes (if market intent)
    MD-->>G: market_context
    G->>O: orchestrate(user_query, context)
    O-->>G: {agents, reason}
    G->>S: parallel specialist calls (Send fan-out)
    S-->>G: agent_outputs
    G->>Y: synthesize(all outputs + contexts)
    Y-->>G: final_answer
    G-->>UI: streaming updates + final answer
    UI-->>U: rendered response
```

## Notes

- Parallelism is handled by `route_specialists` + LangGraph `Send`.
- RAG context is scoped to selected educational agents (`finance_qa`, `tax_education`, `goal_planning`).
- Market context is scoped to market-focused agents (`market_analysis`, `portfolio_analysis`).
- If a provider fails, the workflow degrades gracefully and still produces an answer when possible.
