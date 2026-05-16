"""Input scope guard for finance-only assistant behavior."""

from __future__ import annotations

import re

from utils.symbols import extract_company_alias_tickers, extract_tickers

_FINANCE_KEYWORDS = re.compile(
    r"\b("
    r"finance|financial|money|budget|saving|savings|invest|investing|investment|"
    r"portfolio|allocation|diversification|risk|return|compound|interest|"
    r"stock|stocks|share|shares|bond|bonds|etf|mutual fund|index fund|market|"
    r"trading|price|quote|valuation|earnings|revenue|profit|dividend|"
    r"capital gains|tax|taxes|irs|deduction|credit|withholding|"
    r"ira|roth|401k|hsa|cash flow|net worth|debt|loan|mortgage|"
    r"inflation|fed|recession|headline|headlines"
    r")\b",
    flags=re.IGNORECASE,
)

_MONEY_PATTERN = re.compile(r"(\$ ?\d[\d,]*(?:\.\d+)?)|(\d+% )|(\d+ ?percent)", flags=re.IGNORECASE)

OUT_OF_SCOPE_REPLY = (
    "Please ask a finance-related question. I don't have expertise to provide answers "
    "outside finance/tax educational queries."
)


def is_finance_or_specialist_scope(text: str) -> bool:
    q = (text or "").strip()
    if not q:
        return False
    if extract_tickers(q, max_symbols=1):
        return True
    if extract_company_alias_tickers(q, max_symbols=1):
        return True
    if _FINANCE_KEYWORDS.search(q):
        return True
    if _MONEY_PATTERN.search(q):
        return True
    return False

