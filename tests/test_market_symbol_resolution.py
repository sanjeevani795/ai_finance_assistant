from __future__ import annotations

from core.config import load_config
from data.market_service import MarketDataService


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


def test_resolve_symbols_prefers_explicit_ticker(monkeypatch) -> None:
    cfg = load_config()
    svc = MarketDataService(cfg)

    called = {"n": 0}

    def _fake_get(*args, **kwargs):
        called["n"] += 1
        return _Resp({"quotes": []})

    monkeypatch.setattr("data.market_service.requests.get", _fake_get)

    out = svc.resolve_symbols_from_query("What is GOOGL trading at?")
    assert out == ["GOOGL"]
    assert called["n"] == 0


def test_resolve_symbols_from_company_name_yahoo(monkeypatch) -> None:
    cfg = load_config()
    svc = MarketDataService(cfg)

    def _fake_get(*args, **kwargs):
        return _Resp(
            {
                "quotes": [
                    {"symbol": "GOOGL", "quoteType": "EQUITY"},
                    {"symbol": "GOOG", "quoteType": "EQUITY"},
                ]
            }
        )

    monkeypatch.setattr("data.market_service.requests.get", _fake_get)

    out = svc.resolve_symbols_from_query("What is Google trading at?")
    assert "GOOGL" in out
