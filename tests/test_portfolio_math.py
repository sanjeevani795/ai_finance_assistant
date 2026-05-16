from agents.portfolio_math import (
    herfindahl_hirschman_index,
    normalize_weights,
    parse_weight_lines,
    portfolio_summary_block,
)


def test_parse_and_normalize() -> None:
    w = parse_weight_lines("I hold AAPL 40% and MSFT 60%")
    n = normalize_weights(w)
    assert abs(sum(n.values()) - 1.0) < 1e-6
    assert "AAPL" in n and "MSFT" in n


def test_hhi_full_concentration() -> None:
    h = herfindahl_hirschman_index({"AAPL": 1.0})
    assert abs(h - 1.0) < 1e-6


def test_portfolio_summary_empty_without_weights() -> None:
    assert portfolio_summary_block("What is diversification?") == ""
