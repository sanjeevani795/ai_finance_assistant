"""Unified market data access: yFinance + Alpha Vantage with caching."""

from __future__ import annotations

import logging
import re
from typing import Any

import requests

from core.config import AppConfig, alpha_vantage_key
from data.alpha_vantage import AlphaVantageClient
from data.yfinance_client import yfinance_quote, yfinance_trend_summary
from utils.cache import TTLCache
from utils.retry import retry_call
from utils.symbols import extract_tickers

logger = logging.getLogger(__name__)
_YAHOO_SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search"
_VALID_SYMBOL = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


def _normalize_company_query(text: str) -> str:
    q = (text or "").strip()
    if not q:
        return ""
    q = re.sub(
        r"\b(what|is|the|price|trading|trade|at|stock|quote|of|for|today|right|now)\b",
        " ",
        q,
        flags=re.IGNORECASE,
    )
    q = re.sub(r"[^A-Za-z0-9&.\- ]+", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q


def _format_av_global_quote(payload: dict[str, Any]) -> dict[str, Any]:
    q = payload.get("Global Quote") or {}
    if not isinstance(q, dict):
        return {"symbol": None, "source": "alphavantage", "raw": payload}
    sym = q.get("01. symbol") or q.get("01. Symbol")
    price = q.get("05. price") or q.get("05. Price")
    prev = q.get("08. previous close") or q.get("08. Previous Close")
    pct = q.get("10. change percent") or q.get("10. Change Percent")
    return {
        "symbol": sym,
        "source": "alphavantage",
        "last": float(price) if price not in (None, "") else None,
        "previous_close": float(prev) if prev not in (None, "") else None,
        "change_percent_str": pct,
        "raw_quote": q,
    }


class MarketDataService:
    def __init__(self, cfg: AppConfig) -> None:
        self._cfg = cfg
        self._cache = TTLCache(float(cfg.market_cache_ttl))
        key = alpha_vantage_key()
        self._av = AlphaVantageClient(key, cfg, self._cache) if key else None

    def _search_yahoo_symbols(self, query: str) -> list[str]:
        q = _normalize_company_query(query)
        if not q:
            return []
        cache_key = f"yf:search:{q.lower()}"

        def fetch() -> list[str]:
            def do_http() -> list[str]:
                r = requests.get(
                    _YAHOO_SEARCH_URL,
                    params={"q": q, "quotesCount": 8, "newsCount": 0},
                    timeout=self._cfg.request_timeout,
                )
                r.raise_for_status()
                data = r.json()
                quotes = data.get("quotes") if isinstance(data, dict) else []
                out: list[str] = []
                for item in quotes or []:
                    if not isinstance(item, dict):
                        continue
                    sym = str(item.get("symbol") or "").strip().upper()
                    qt = str(item.get("quoteType") or "").upper()
                    if qt not in {"EQUITY", "ETF"}:
                        continue
                    if not _VALID_SYMBOL.match(sym):
                        continue
                    if sym not in out:
                        out.append(sym)
                    if len(out) >= 4:
                        break
                return out

            return retry_call(
                do_http,
                max_attempts=self._cfg.max_retries,
                backoff_seconds=self._cfg.retry_backoff,
                operation=f"yahoo symbol search {q}",
            )

        try:
            return self._cache.get_or_set(cache_key, fetch)
        except Exception as exc:  # noqa: BLE001
            logger.info("Yahoo symbol search failed for query '%s': %s", q, exc)
            return []

    def _search_alpha_vantage_symbols(self, query: str) -> list[str]:
        if self._av is None:
            return []
        q = _normalize_company_query(query)
        if not q:
            return []
        try:
            data = self._av.symbol_search(q)
        except Exception as exc:  # noqa: BLE001
            logger.info("Alpha Vantage symbol search failed for query '%s': %s", q, exc)
            return []

        out: list[str] = []
        for m in data.get("bestMatches") or []:
            if not isinstance(m, dict):
                continue
            sym = str(m.get("1. symbol") or "").strip().upper()
            region = str(m.get("4. region") or "")
            if not _VALID_SYMBOL.match(sym):
                continue
            if region and "United States" not in region:
                continue
            if sym not in out:
                out.append(sym)
            if len(out) >= 4:
                break
        return out

    def resolve_symbols_from_query(self, query: str, *, max_symbols: int = 3) -> list[str]:
        explicit = extract_tickers(query, max_symbols=max_symbols)
        if explicit:
            return explicit

        resolved = self._search_yahoo_symbols(query)
        if not resolved:
            resolved = self._search_alpha_vantage_symbols(query)
        return resolved[:max_symbols]

    def quote(self, symbol: str) -> dict[str, Any]:
        sym = symbol.upper().strip()
        errors: list[str] = []

        if self._cfg.prefer_yfinance:
            try:
                return yfinance_quote(sym, self._cfg, self._cache)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"yFinance: {exc}")
                logger.info("Falling back from yFinance for %s", sym)

        if self._av is not None:
            try:
                raw = self._av.global_quote(sym)
                return _format_av_global_quote(raw)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"AlphaVantage: {exc}")
                logger.warning("Alpha Vantage quote failed for %s", sym)

        if not self._cfg.prefer_yfinance:
            try:
                return yfinance_quote(sym, self._cfg, self._cache)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"yFinance: {exc}")

        raise RuntimeError("; ".join(errors) or "Market data unavailable.")

    def trend(self, symbol: str) -> dict[str, Any]:
        sym = symbol.upper().strip()
        try:
            return yfinance_trend_summary(sym, self._cfg, self._cache)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Trend summary failed (%s): %s", sym, exc)
            return {"symbol": sym, "source": "yfinance", "error": str(exc)}

    def quotes_for_symbols(self, symbols: list[str]) -> str:
        """Human-readable block for LLM context."""
        lines: list[str] = []
        for s in symbols:
            try:
                q = self.quote(s)
                t = self.trend(s)
                lines.append(f"{q.get('symbol')}: last={q.get('last')} currency={q.get('currency')} source={q.get('source')}")
                if t.get("approx_1w_change_pct") is not None:
                    lines.append(
                        f"  ~1w change: {t.get('approx_1w_change_pct'):.2f}% | ~1m: {t.get('approx_1m_change_pct')}"
                    )
            except Exception as exc:  # noqa: BLE001
                lines.append(f"{s}: ERROR {exc}")
        return "\n".join(lines) if lines else ""
