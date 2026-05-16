#!/usr/bin/env python3
"""Build FAISS index from sample KB + optional files in `data/raw_docs/`."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from core.config import load_config, require_openai_key  # noqa: E402
from rag.faiss_store import build_faiss_from_documents, save_faiss  # noqa: E402
from rag.ingest import chunk_documents, load_text_file  # noqa: E402
from utils.logging_config import setup_logging  # noqa: E402
import logging  # noqa: E402

logger = logging.getLogger(__name__)


def main() -> None:
    cfg = load_config()
    setup_logging(cfg.logs_dir)
    require_openai_key()

    docs = []
    sample = ROOT / "data" / "sample_kb.txt"
    if sample.is_file():
        docs.extend(
            load_text_file(
                sample,
                source_url="internal://sample_kb",
                category="Personal Finance / Investing",
            )
        )
    else:
        logger.warning("Sample file not found, continuing without it: %s", sample)

    raw_docs_dir = ROOT / "data" / "raw_docs"
    if raw_docs_dir.is_dir():
        supported = ("*.txt", "*.md")
        for pattern in supported:
            for p in sorted(raw_docs_dir.rglob(pattern)):
                try:
                    docs.extend(
                        load_text_file(
                            p,
                            source_url=f"internal://raw_docs/{p.relative_to(raw_docs_dir)}",
                            category="User Docs",
                        )
                    )
                except Exception:  # noqa: BLE001
                    logger.exception("Failed to load raw doc: %s", p)
    else:
        logger.info("Optional raw docs dir not found: %s", raw_docs_dir)

    if not docs:
        raise SystemExit("No source docs found. Add data/sample_kb.txt or files in data/raw_docs/.")

    logger.info("Loaded %s source document(s) for indexing.", len(docs))
    chunks = chunk_documents(docs, cfg)
    store = build_faiss_from_documents(chunks, cfg)
    save_faiss(store, cfg)
    logger.info("Demo FAISS index built at %s", cfg.faiss_index_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
