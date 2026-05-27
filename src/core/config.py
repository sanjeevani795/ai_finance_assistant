"""Load YAML + env; resolve paths relative to project root."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def _project_root() -> Path:
    # ai_finance_assistant/ directory (parent of src/)
    return Path(__file__).resolve().parents[2]


@dataclass
class AppConfig:
    openai_chat_model: str
    openai_embedding_model: str
    openai_temperature: float
    faiss_index_dir: Path
    faiss_index_name: str
    logs_dir: Path
    raw_docs_dir: Path
    market_cache_ttl: int
    alpha_vantage_base_url: str
    prefer_yfinance: bool
    request_timeout: float
    max_retries: int
    retry_backoff: float
    rag_chunk_size: int
    rag_chunk_overlap: int
    rag_retrieval_k: int
    max_agents_per_query: int
    news_rss_urls: list[str]
    news_request_timeout_seconds: float
    news_max_items_per_feed: int
    raw: dict[str, Any]


def load_config(config_path: Path | None = None) -> AppConfig:
    load_dotenv()
    root = _project_root()
    path = config_path or (root / "config.yaml")
    if not path.is_file():
        raise FileNotFoundError(f"Missing config file: {path}")

    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    oa = raw.get("openai") or {}
    paths = raw.get("paths") or {}
    market = raw.get("market") or {}
    rag = raw.get("rag") or {}
    wf = raw.get("workflow") or {}
    news = raw.get("news") or {}
    rss = news.get("rss_urls") or ["https://feeds.reuters.com/reuters/businessNews"]
    if isinstance(rss, str):
        rss = [rss]

    faiss_dir_cfg = str(paths.get("faiss_index_dir") or "data/faiss_index")
    # On Hugging Face Spaces, prefer persistent volume if available.
    if os.getenv("SPACE_ID") and not os.getenv("FAISS_INDEX_DIR"):
        faiss_dir = Path("/data/faiss_index")
    else:
        faiss_dir = Path(os.getenv("FAISS_INDEX_DIR", faiss_dir_cfg))
        if not faiss_dir.is_absolute():
            faiss_dir = root / faiss_dir
    logs_dir = root / (paths.get("logs_dir") or "logs")
    raw_docs = root / (paths.get("raw_docs_dir") or "data/raw_docs")

    cfg = AppConfig(
        openai_chat_model=str(oa.get("chat_model", "gpt-4o-mini")),
        openai_embedding_model=str(oa.get("embedding_model", "text-embedding-3-large")),
        openai_temperature=float(oa.get("temperature", 0.2)),
        faiss_index_dir=faiss_dir,
        faiss_index_name=str(paths.get("faiss_index_name", "finance_kb")),
        logs_dir=logs_dir,
        raw_docs_dir=raw_docs,
        market_cache_ttl=int(market.get("cache_ttl_seconds", 300)),
        alpha_vantage_base_url=str(
            market.get("alpha_vantage_base_url", "https://www.alphavantage.co/query")
        ),
        prefer_yfinance=bool(market.get("prefer_yfinance", True)),
        request_timeout=float(market.get("request_timeout_seconds", 30)),
        max_retries=int(market.get("max_retries", 3)),
        retry_backoff=float(market.get("retry_backoff_seconds", 1.5)),
        rag_chunk_size=int(rag.get("chunk_size", 900)),
        rag_chunk_overlap=int(rag.get("chunk_overlap", 120)),
        rag_retrieval_k=int(rag.get("retrieval_k", 6)),
        max_agents_per_query=int(wf.get("max_agents_per_query", 4)),
        news_rss_urls=[str(u) for u in rss],
        news_request_timeout_seconds=float(news.get("request_timeout_seconds", 12)),
        news_max_items_per_feed=int(news.get("max_items_per_feed", 4)),
        raw=raw,
    )

    logger.debug("Loaded config from %s", path)
    return cfg


def require_openai_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set. Copy .env.example to .env and add your key.")
    return key


def alpha_vantage_key() -> Optional[str]:
    k = os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
    return k or None
