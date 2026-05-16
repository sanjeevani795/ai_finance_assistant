#!/usr/bin/env python3
"""Build a small FAISS index from `data/sample_kb.txt` for local demos."""

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

    sample = ROOT / "data" / "sample_kb.txt"
    if not sample.is_file():
        raise SystemExit(f"Missing sample file: {sample}")

    docs = load_text_file(
        sample,
        source_url="internal://sample_kb",
        category="Personal Finance / Investing",
    )
    chunks = chunk_documents(docs, cfg)
    store = build_faiss_from_documents(chunks, cfg)
    save_faiss(store, cfg)
    logger.info("Demo FAISS index built at %s", cfg.faiss_index_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
