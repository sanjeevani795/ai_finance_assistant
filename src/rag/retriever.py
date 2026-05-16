"""High-level retrieval over the finance knowledge base."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.config import AppConfig

if TYPE_CHECKING:
    from langchain_community.vectorstores import FAISS

logger = logging.getLogger(__name__)


class FinanceRetriever:
    def __init__(self, cfg: AppConfig, store: "FAISS | None") -> None:
        self._cfg = cfg
        self._store = store

    def retrieve(self, query: str) -> str:
        if not query.strip():
            return ""
        if self._store is None:
            return ""
        try:
            docs = self._store.similarity_search(query, k=self._cfg.rag_retrieval_k)
        except Exception:
            logger.exception("RAG retrieval failed.")
            return ""

        blocks: list[str] = []
        for i, d in enumerate(docs, start=1):
            meta = d.metadata or {}
            src = meta.get("source_url") or meta.get("source") or meta.get("source_file", "unknown")
            cat = meta.get("category", "")
            head = f"[{i}] source={src}"
            if cat:
                head += f" category={cat}"
            blocks.append(f"{head}\n{d.page_content.strip()}")
        return "\n\n---\n\n".join(blocks)
