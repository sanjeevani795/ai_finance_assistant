"""Chunk text and optional URL sources into LangChain Documents."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.config import AppConfig

logger = logging.getLogger(__name__)


def make_splitter(cfg: AppConfig) -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=cfg.rag_chunk_size,
        chunk_overlap=cfg.rag_chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )


def load_text_file(path: Path, *, source_url: str | None = None, category: str | None = None) -> list[Document]:
    loader = TextLoader(str(path), encoding="utf-8")
    docs = loader.load()
    meta_base: dict[str, Any] = {"source_file": str(path)}
    if source_url:
        meta_base["source_url"] = source_url
    if category:
        meta_base["category"] = category
    for d in docs:
        d.metadata = {**meta_base, **d.metadata}
    return docs


def chunk_documents(documents: list[Document], cfg: AppConfig) -> list[Document]:
    splitter = make_splitter(cfg)
    chunks = splitter.split_documents(documents)
    logger.info("Split %s docs into %s chunks.", len(documents), len(chunks))
    return chunks


def documents_from_strings(
    items: list[dict[str, Any]],
    *,
    cfg: AppConfig,
) -> list[Document]:
    """items: {text, metadata?}"""
    base_docs: list[Document] = []
    for it in items:
        base_docs.append(
            Document(page_content=str(it["text"]), metadata=dict(it.get("metadata") or {}))
        )
    return chunk_documents(base_docs, cfg)
