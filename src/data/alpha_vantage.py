"""Alpha Vantage REST client with caching and soft rate-limit handling."""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import Any

import requests

from core.config import AppConfig
from utils.cache import TTLCache
from utils.retry import retry_call

logger = logging.getLogger(__name__)

# Free tier is very low; track recent calls to avoid hammering.
_AV_WINDOW_SEC = 60.0
_AV_MAX_PER_WINDOW = 5


class AlphaVantageClient:
    def __init__(self, api_key: str, cfg: AppConfig, cache: TTLCache) -> None:
        self._key = api_key
        self._cfg = cfg
        self._cache = cache
        self._recent: deque[float] = deque()

    def _throttle(self) -> None:
        now = time.monotonic()
        while self._recent and now - self._recent[0] > _AV_WINDOW_SEC:
            self._recent.popleft()
        if len(self._recent) >= _AV_MAX_PER_WINDOW:
            sleep_for = _AV_WINDOW_SEC - (now - self._recent[0])
            if sleep_for > 0:
                logger.warning("Alpha Vantage soft throttle: sleeping %.1fs", sleep_for)
                time.sleep(sleep_for)

    def global_quote(self, symbol: str) -> dict[str, Any]:
        sym = symbol.upper().strip()
        cache_key = f"av:GLOBAL_QUOTE:{sym}"

        def fetch() -> dict[str, Any]:
            self._throttle()
            self._recent.append(time.monotonic())

            def do_http() -> dict[str, Any]:
                params = {
                    "function": "GLOBAL_QUOTE",
                    "symbol": sym,
                    "apikey": self._key,
                }
                r = requests.get(
                    self._cfg.alpha_vantage_base_url,
                    params=params,
                    timeout=self._cfg.request_timeout,
                )
                r.raise_for_status()
                data = r.json()
                if not isinstance(data, dict):
                    raise ValueError("Unexpected Alpha Vantage payload.")
                note = data.get("Note") or data.get("Information")
                if note:
                    logger.warning("Alpha Vantage message: %s", note)
                err = data.get("Error Message")
                if err:
                    raise RuntimeError(str(err))
                return data

            return retry_call(
                do_http,
                max_attempts=self._cfg.max_retries,
                backoff_seconds=self._cfg.retry_backoff,
                operation=f"AlphaVantage GLOBAL_QUOTE {sym}",
            )

        return self._cache.get_or_set(cache_key, fetch)

    def symbol_search(self, keywords: str) -> dict[str, Any]:
        q = keywords.strip()
        if not q:
            return {}
        cache_key = f"av:SYMBOL_SEARCH:{q.lower()}"

        def fetch() -> dict[str, Any]:
            self._throttle()
            self._recent.append(time.monotonic())

            def do_http() -> dict[str, Any]:
                params = {
                    "function": "SYMBOL_SEARCH",
                    "keywords": q,
                    "apikey": self._key,
                }
                r = requests.get(
                    self._cfg.alpha_vantage_base_url,
                    params=params,
                    timeout=self._cfg.request_timeout,
                )
                r.raise_for_status()
                data = r.json()
                if not isinstance(data, dict):
                    raise ValueError("Unexpected Alpha Vantage payload.")
                err = data.get("Error Message")
                if err:
                    raise RuntimeError(str(err))
                return data

            return retry_call(
                do_http,
                max_attempts=self._cfg.max_retries,
                backoff_seconds=self._cfg.retry_backoff,
                operation=f"AlphaVantage SYMBOL_SEARCH {q}",
            )

        return self._cache.get_or_set(cache_key, fetch)
