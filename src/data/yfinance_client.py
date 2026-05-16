"""yFinance-backed quotes (unofficial Yahoo data — good for prototypes)."""

from __future__ import annotations

import logging
from typing import Any

from core.config import AppConfig
from utils.cache import TTLCache
from utils.retry import retry_call

logger = logging.getLogger(__name__)


def _yf_ticker(symbol: str) -> str:
    return symbol.strip().upper()


def _history_with_fallbacks(ticker: Any, periods: tuple[str, ...]):
    """Try a small sequence of history requests; yfinance can return empty intermittently."""
    for period in periods:
        try:
            hist = ticker.history(period=period, interval="1d", auto_adjust=False)
        except TypeError:
            # Older yfinance versions may not support all kwargs consistently.
            hist = ticker.history(period=period)
        if hist is not None and not hist.empty:
            return hist
    return None


def yfinance_quote(symbol: str, cfg: AppConfig, cache: TTLCache) -> dict[str, Any]:
    sym = _yf_ticker(symbol)
    cache_key = f"yf:quote:{sym}"

    def fetch() -> dict[str, Any]:
        def do_fetch() -> dict[str, Any]:
            import yfinance as yf

            t = yf.Ticker(sym)
            last = None
            prev = None
            cur = None
            fast = getattr(t, "fast_info", None)
            if fast is not None:
                last = getattr(fast, "last_price", None) or getattr(fast, "lastPrice", None)
                prev = getattr(fast, "previous_close", None) or getattr(fast, "previousClose", None)
                cur = getattr(fast, "currency", None) or getattr(fast, "currency_code", None)
            if last is None:
                hist = _history_with_fallbacks(t, ("5d", "1mo"))
                if hist is None or hist.empty:
                    raise RuntimeError(f"No yFinance data for symbol {sym}.")
                last = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else last
            change = None
            if last is not None and prev not in (None, 0):
                change = (float(last) - float(prev)) / float(prev) * 100.0
            return {
                "symbol": sym,
                "source": "yfinance",
                "last": float(last) if last is not None else None,
                "previous_close": float(prev) if prev is not None else None,
                "currency": cur,
                "pct_change_vs_prev_close": change,
            }

        return retry_call(
            do_fetch,
            max_attempts=cfg.max_retries,
            backoff_seconds=cfg.retry_backoff,
            operation=f"yfinance quote {sym}",
        )

    try:
        return cache.get_or_set(cache_key, fetch)
    except Exception:
        logger.exception("yFinance quote failed for %s", sym)
        raise


def yfinance_trend_summary(symbol: str, cfg: AppConfig, cache: TTLCache) -> dict[str, Any]:
    """Very small trend snapshot from recent daily closes."""
    sym = _yf_ticker(symbol)
    cache_key = f"yf:trend:{sym}"

    def fetch() -> dict[str, Any]:
        def do_fetch() -> dict[str, Any]:
            import yfinance as yf

            t = yf.Ticker(sym)
            hist = _history_with_fallbacks(t, ("3mo", "6mo", "1y"))
            if hist is None or hist.empty:
                raise RuntimeError(f"No history for {sym}.")
            closes = hist["Close"].astype(float)
            last = float(closes.iloc[-1])
            week_ago = float(closes.iloc[-5]) if len(closes) >= 5 else last
            month_ago = float(closes.iloc[-21]) if len(closes) >= 21 else last
            return {
                "symbol": sym,
                "source": "yfinance",
                "last_close": last,
                "approx_1w_change_pct": (last - week_ago) / week_ago * 100.0 if week_ago else None,
                "approx_1m_change_pct": (last - month_ago) / month_ago * 100.0 if month_ago else None,
            }

        return retry_call(
            do_fetch,
            max_attempts=cfg.max_retries,
            backoff_seconds=cfg.retry_backoff,
            operation=f"yfinance trend {sym}",
        )

    return cache.get_or_set(cache_key, fetch)
