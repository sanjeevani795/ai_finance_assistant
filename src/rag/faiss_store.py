"""Build / load FAISS vector store with OpenAI embeddings.

LangChain/FAISS/NumPy are imported lazily to avoid heavy imports (and some macOS
NumPy init edge cases) when only the workflow graph is loaded for tests.
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any

from core.config import AppConfig, require_openai_key

logger = logging.getLogger(__name__)


def _embedding_model(cfg: AppConfig):
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        api_key=require_openai_key(),
        model=cfg.openai_embedding_model,
    )


def faiss_paths(cfg: AppConfig) -> tuple[Path, Path]:
    cfg.faiss_index_dir.mkdir(parents=True, exist_ok=True)
    base = cfg.faiss_index_dir / cfg.faiss_index_name
    return base.with_suffix(".faiss"), base.with_suffix(".pkl")


def load_faiss(cfg: AppConfig) -> Any:
    from langchain_community.vectorstores import FAISS

    faiss_file, pkl_file = faiss_paths(cfg)
    if not faiss_file.is_file() or not pkl_file.is_file():
        logger.info("FAISS index not found at %s; running without RAG context.", faiss_file)
        return None
    try:
        vs = FAISS.load_local(
            folder_path=str(cfg.faiss_index_dir),
            embeddings=_embedding_model(cfg),
            index_name=cfg.faiss_index_name,
            allow_dangerous_deserialization=True,
        )
        logger.info("Loaded FAISS index '%s'.", cfg.faiss_index_name)
        return vs
    except Exception:
        logger.exception("Failed to load FAISS index.")
        return None


def save_faiss(store: Any, cfg: AppConfig) -> None:
    cfg.faiss_index_dir.mkdir(parents=True, exist_ok=True)
    store.save_local(folder_path=str(cfg.faiss_index_dir), index_name=cfg.faiss_index_name)
    logger.info("Saved FAISS index to %s", cfg.faiss_index_dir)


def build_faiss_from_documents(documents: list[Any], cfg: AppConfig) -> Any:
    from langchain_community.vectorstores import FAISS

    if not documents:
        raise ValueError("No documents to index.")
    emb = _embedding_model(cfg)
    logger.info("Embedding %s chunks into FAISS…", len(documents))
    return FAISS.from_documents(documents, emb)


def documents_from_records(records: list[dict[str, Any]]) -> list[Any]:
    """records: {page_content, metadata dict}"""
    from langchain_core.documents import Document

    out: list[Any] = []
    for r in records:
        out.append(Document(page_content=str(r["page_content"]), metadata=dict(r.get("metadata") or {})))
    return out


def persist_doc_manifest(cfg: AppConfig, manifest: list[dict[str, Any]]) -> None:
    cfg.faiss_index_dir.mkdir(parents=True, exist_ok=True)
    path = cfg.faiss_index_dir / "manifest.pkl"
    with path.open("wb") as f:
        pickle.dump(manifest, f)
    logger.info("Wrote ingest manifest (%s sources) to %s", len(manifest), path)
