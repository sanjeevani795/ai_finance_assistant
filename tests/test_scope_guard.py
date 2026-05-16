from utils.scope_guard import is_finance_or_specialist_scope


def test_scope_guard_accepts_finance_question() -> None:
    assert is_finance_or_specialist_scope("How should I diversify my retirement portfolio?")


def test_scope_guard_accepts_ticker_question() -> None:
    assert is_finance_or_specialist_scope("What is AAPL trading at today?")


def test_scope_guard_accepts_company_alias_question() -> None:
    assert is_finance_or_specialist_scope("Any headlines about Nvidia stock?")


def test_scope_guard_rejects_non_finance_question() -> None:
    assert not is_finance_or_specialist_scope("Write a poem about mountains.")

