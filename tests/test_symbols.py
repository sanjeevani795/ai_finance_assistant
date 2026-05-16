from utils.symbols import extract_tickers, query_mentions_market


def test_extract_tickers_basic() -> None:
    s = extract_tickers("Compare AAPL vs MSFT for me")
    assert "AAPL" in s and "MSFT" in s


def test_extract_tickers_dedupes() -> None:
    s = extract_tickers("AAPL AAPL")
    assert s == ["AAPL"]


def test_query_mentions_market_true_for_price_query() -> None:
    assert query_mentions_market("What is Google trading at right now?")


def test_query_mentions_market_false_for_tax_education_query() -> None:
    assert not query_mentions_market("Explain the difference between a traditional IRA and a Roth IRA.")
