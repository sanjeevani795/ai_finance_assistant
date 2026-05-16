"""Deterministic portfolio helpers (weights, concentration, simple return math)."""

from __future__ import annotations

import re

# "AAPL 40%" or "AAPL: 0.4" or "MSFT 30% GOOG 30%"
_WEIGHT_PAT = re.compile(
    r"\b([A-Z]{1,5})\b\s*(?:[:=]\s*)?(\d+(?:\.\d+)?)\s*(?:%|percent)?",
    re.IGNORECASE,
)


def parse_weight_lines(text: str) -> dict[str, float]:
    """Extract ticker → weight from free text. Weights may be fractions or whole percents."""
    out: dict[str, float] = {}
    for m in _WEIGHT_PAT.finditer(text or ""):
        sym = m.group(1).upper()
        val = float(m.group(2))
        if val > 1.0 and val <= 100.0:
            val = val / 100.0
        if 0 < val <= 1.0:
            out[sym] = val
    return out


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    """Return weights that sum to 1.0 (equal split if sum is 0)."""
    if not weights:
        return {}
    s = sum(weights.values())
    if s <= 0:
        return {}
    return {k: v / s for k, v in weights.items()}


def herfindahl_hirschman_index(weights: dict[str, float]) -> float:
    """Concentration in [0,1]; higher means more concentrated."""
    w = normalize_weights(weights)
    if not w:
        return 0.0
    return sum(v * v for v in w.values())


def effective_number_of_assets(weights: dict[str, float]) -> float:
    """Inverse HHI; interpretable as 'effective' count of equal-weight sleeves."""
    h = herfindahl_hirschman_index(weights)
    if h <= 0:
        return 0.0
    return 1.0 / h


def portfolio_summary_block(user_query: str) -> str:
    """Build a short, factual block for the LLM from parsed weights (no price data)."""
    raw = parse_weight_lines(user_query)
    if not raw:
        return ""
    w = normalize_weights(raw)
    if not w:
        return ""
    hhi = herfindahl_hirschman_index(raw)
    eff_n = effective_number_of_assets(raw)
    lines = [
        "Parsed portfolio weights (from your message, normalized to sum to 1):",
        ", ".join(f"{k}: {v:.4f}" for k, v in sorted(w.items())),
        f"Herfindahl-Hirschman index (concentration): {hhi:.4f}",
        f"Effective number of equal-risk sleeves (1/HHI): {eff_n:.2f}",
    ]
    return "\n".join(lines)
