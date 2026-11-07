from datetime import datetime, timezone

import pandas as pd
import pytest

from agent import feeds

NOW = datetime(2026, 11, 8, 0, 7, tzinfo=timezone.utc)
D = 86400


def cb_rows(n=5, last_open=datetime(2026, 11, 8, tzinfo=timezone.utc)):
    """Coinbase order: newest first, [time, low, high, open, close, volume]. Last row is still forming."""
    t0 = int(last_open.timestamp())
    return [[t0 - i * D, 90.0, 110.0, 100.0 + i, 101.0 + i, 5.0] for i in range(n)]


def fake(responses):
    def get(url):
        for key, val in responses.items():
            if key in url:
                if isinstance(val, Exception):
                    raise val
                return val
        raise AssertionError(f"unexpected url {url}")
    return get


def test_coinbase_drops_forming_bar_and_sorts():
    df, forming_open = feeds.coinbase_candles("BTC-USD", D, NOW, 4, get=fake({"candles": cb_rows()}))
    assert df.index[-1] == pd.Timestamp("2026-11-07", tz="UTC")
    assert df.index.is_monotonic_increasing and len(df) == 4
    assert forming_open == 100.0  # open of the 2026-11-08 bar


def test_coinbase_rejects_bad_bars():
    rows = cb_rows()
    rows[2][2] = 50.0  # high below open/close
    with pytest.raises(feeds.FeedError):
        feeds.coinbase_candles("BTC-USD", D, NOW, 4, get=fake({"candles": rows}))
    with pytest.raises(feeds.FeedError):
        feeds.coinbase_candles("BTC-USD", D, NOW, 4, get=fake({"candles": []}))


def test_gap_detection():
    rows = cb_rows(6)
    del rows[3]
    df, _ = feeds.coinbase_candles("BTC-USD", D, NOW, 6, get=fake({"candles": rows}))
    assert feeds.gaps(df, D) == 1


def test_quote_parsing_and_crossed_book():
    q = feeds.coinbase_quote("BTC-USD", get=fake({"ticker": {"bid": "99.9", "ask": "100.1", "price": "100", "time": "x"}}))
    assert q["bid"] == 99.9 and q["ask"] == 100.1
    with pytest.raises(feeds.FeedError):
        feeds.coinbase_quote("BTC-USD", get=fake({"ticker": {"bid": "101", "ask": "100", "price": "100"}}))
    with pytest.raises(feeds.FeedError):
        feeds.coinbase_quote("BTC-USD", get=fake({"ticker": {"message": "NotFound"}}))


BAR = pd.Timestamp("2026-11-07", tz="UTC")


def binance_rows():
    o = int(BAR.timestamp() * 1000)
    return [[o - 86400000, "1", "1", "1", "99", "1", o - 1, 0, 0, 0, 0, 0],
            [o, "1", "1", "1", "100.5", "1", o + 86400000 - 1, 0, 0, 0, 0, 0],
            [o + 86400000, "1", "1", "1", "777", "1", o + 2 * 86400000 - 1, 0, 0, 0, 0, 0]]  # forming


def test_binance_close_for_bar():
    assert feeds.binance_daily_close("BTCUSDT", BAR, NOW, get=fake({"klines": binance_rows()})) == 100.5


def test_kraken_close_for_bar():
    t = int(BAR.timestamp())
    resp = {"error": [], "result": {"XXBTZUSD": [[t - D, "1", "1", "1", "99", "1", "1", 1],
                                                 [t, "1", "1", "1", "100.7", "1", "1", 1]], "last": t}}
    assert feeds.kraken_daily_close("XBTUSD", BAR, NOW, get=fake({"OHLC": resp})) == 100.7


def test_secondary_falls_back_to_kraken():
    t = int(BAR.timestamp())
    get = fake({"klines": feeds.FeedError("451 blocked"),
                "OHLC": {"error": [], "result": {"XXBTZUSD": [[t, "1", "1", "1", "100.7", "1", "1", 1]]}}})
    assert feeds.secondary_close([("binance", "BTCUSDT"), ("kraken", "XBTUSD")], BAR, NOW, get=get) == ("kraken", 100.7)


def test_secondary_all_fail():
    get = fake({"klines": feeds.FeedError("down"), "OHLC": {"error": ["EService:Unavailable"]}})
    with pytest.raises(feeds.FeedError):
        feeds.secondary_close([("binance", "BTCUSDT"), ("kraken", "XBTUSD")], BAR, NOW, get=get)


def test_http_retries_then_raises(monkeypatch):
    calls = []

    def boom(*a, **k):
        calls.append(1)
        raise OSError("connection reset")
    monkeypatch.setattr(feeds.urllib.request, "urlopen", boom)
    monkeypatch.setattr(feeds.time, "sleep", lambda s: None)
    with pytest.raises(feeds.FeedError):
        feeds.http_get_json("https://example.invalid/x", retries=2)
    assert len(calls) == 3
