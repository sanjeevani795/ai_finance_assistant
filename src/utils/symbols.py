"""Heuristic ticker extraction from natural language."""

from __future__ import annotations

import re

_TICKER = re.compile(r"\b([A-Z]{1,5})\b")
_MARKET_HINT = re.compile(
    r"\b("
    r"ticker|stock|stocks|share|shares|price|quote|trading|trade|market|"
    r"nasdaq|nyse|s&p|dow|etf|equity|valuation|earnings|pe|p/e|dividend|"
    r"bull|bear|rally|selloff|volatility|52-week|all-time high|ath|"
    r"aapl|msft|googl|goog|amzn|meta|nvda|tsla|spy|qqq"
    r")\b",
    flags=re.IGNORECASE,
)

_COMPANY_ALIASES: tuple[tuple[str, str], ...] = (
    ("nvidia", "NVDA"),
    ("apple", "AAPL"),
    ("microsoft", "MSFT"),
    ("google", "GOOGL"),
    ("alphabet", "GOOGL"),
    ("amazon", "AMZN"),
    ("meta", "META"),
    ("tesla", "TSLA"),
)


def extract_tickers(text: str, *, max_symbols: int = 8) -> list[str]:
    # Exclude common English words mistaken for tickers (very small guard list).
    stop = {
        "A",
        "I",
        "THE",
        "AND",
        "OR",
        "ETF",
        "IRA",
        "ROTH",
        "SEP",
        "LLC",
        "USA",
        "USD",
        "EPS",
        "YOY",
        "CEO",
        "IPO",
        "GDP",
        "CPI",
        "Fed",
    }
    out: list[str] = []
    for m in _TICKER.finditer(text or ""):
        sym = m.group(1)
        if sym in stop:
            continue
        if sym not in out:
            out.append(sym)
        if len(out) >= max_symbols:
            break
    return out


def query_mentions_market(text: str) -> bool:
    q = (text or "").strip()
    if not q:
        return False
    if extract_tickers(q, max_symbols=1):
        return True
    return _MARKET_HINT.search(q) is not None


def extract_company_alias_tickers(text: str, *, max_symbols: int = 8) -> list[str]:
    q = (text or "").lower()
    if not q:
        return []
    out: list[str] = []
    for alias, sym in _COMPANY_ALIASES:
        if re.search(rf"\b{re.escape(alias)}\b", q):
            if sym not in out:
                out.append(sym)
            if len(out) >= max_symbols:
                break
    return out
