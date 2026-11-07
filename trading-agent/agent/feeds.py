"""Public market data. No API keys, read-only.

Primary: Coinbase Exchange public REST (the venue's own USD prices).
Secondary (cross-check only): Binance spot mirror, then Kraken.
Every function takes an injectable `get` so tests run on recorded fixtures.
A bar is used only after it has CLOSED; still-forming bars are dropped.
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timedelta, timezone

import pandas as pd

UA = "paper-trader/1.0 (+github.com/calebkemp310/calebkemp310)"
COINBASE = "https://api.exchange.coinbase.com"
BINANCE = "https://data-api.binance.vision/api/v3/klines"
KRAKEN = "https://api.kraken.com/0/public/OHLC"


class FeedError(Exception):
    pass


def http_get_json(url: str, retries: int = 2, timeout: float = 20.0):
    delay = 1.0
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except Exception as e:  # network, HTTP, JSON
            last = e
            if attempt < retries:
                time.sleep(delay)
                delay *= 2
    raise FeedError(f"GET {url.split('?')[0]} failed: {last}")


def _iso(t: datetime) -> str:
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def coinbase_candles(product: str, granularity: int, now: datetime, bars: int, get=http_get_json):
    """Returns (closed_bars_df, forming_open). Index = bar OPEN time (UTC)."""
    start = now - timedelta(seconds=granularity * (bars + 1))
    url = f"{COINBASE}/products/{product}/candles?granularity={granularity}&start={_iso(start)}&end={_iso(now)}"
    rows = get(url)
    if not isinstance(rows, list) or not rows:
        raise FeedError(f"{product}: empty candle response")
    df = pd.DataFrame(rows, columns=["t", "low", "high", "open", "close", "volume"]).astype(float)
    df = df.drop_duplicates("t").sort_values("t")
    df.index = pd.to_datetime(df["t"].astype("int64"), unit="s", utc=True)
    df.index.name = "time"
    close_time = df.index + pd.Timedelta(seconds=granularity)
    closed = df[close_time <= pd.Timestamp(now)]
    forming = df[close_time > pd.Timestamp(now)]
    forming_open = float(forming["open"].iloc[-1]) if len(forming) else None
    closed = closed[["open", "high", "low", "close", "volume"]]
    _validate(closed, product)
    return closed, forming_open


def _validate(df: pd.DataFrame, product: str) -> None:
    if df.empty:
        raise FeedError(f"{product}: no closed bars")
    if (df[["open", "high", "low", "close"]] <= 0).any().any():
        raise FeedError(f"{product}: non-positive prices")
    bad = (df["high"] < df[["open", "close"]].max(axis=1) - 1e-9) | (df["low"] > df[["open", "close"]].min(axis=1) + 1e-9)
    if bad.any():
        raise FeedError(f"{product}: {int(bad.sum())} bars with high/low outside open/close")


def gaps(df: pd.DataFrame, granularity: int) -> int:
    return int((df.index.to_series().diff().dropna() > pd.Timedelta(seconds=granularity)).sum())


def coinbase_quote(product: str, get=http_get_json) -> dict:
    d = get(f"{COINBASE}/products/{product}/ticker")
    try:
        q = {"bid": float(d["bid"]), "ask": float(d["ask"]), "price": float(d["price"]), "time": d.get("time")}
    except (KeyError, TypeError, ValueError) as e:
        raise FeedError(f"{product}: bad ticker {d}") from e
    if not 0 < q["bid"] <= q["ask"]:
        raise FeedError(f"{product}: crossed or empty book {q}")
    return q


def binance_daily_close(symbol: str, bar_open: pd.Timestamp, now: datetime, get=http_get_json) -> float:
    rows = get(f"{BINANCE}?symbol={symbol}&interval=1d&limit=5")
    now_ms = int(now.timestamp() * 1000)
    target = int(bar_open.timestamp() * 1000)
    for r in rows:
        if int(r[0]) == target and int(r[6]) < now_ms:
            return float(r[4])
    raise FeedError(f"binance {symbol}: bar {bar_open.date()} not found")


def kraken_daily_close(pair: str, bar_open: pd.Timestamp, now: datetime, get=http_get_json) -> float:
    d = get(f"{KRAKEN}?pair={pair}&interval=1440&since={int(bar_open.timestamp()) - 86400}")
    if d.get("error"):
        raise FeedError(f"kraken {pair}: {d['error']}")
    key = next(k for k in d["result"] if k != "last")
    target = int(bar_open.timestamp())
    for r in d["result"][key]:
        if int(r[0]) == target and target + 86400 <= now.timestamp():
            return float(r[4])
    raise FeedError(f"kraken {pair}: bar {bar_open.date()} not found")


SECONDARY_FETCH = {"binance": binance_daily_close, "kraken": kraken_daily_close}


def secondary_close(sources: list, bar_open: pd.Timestamp, now: datetime, get=http_get_json):
    """First secondary that answers: (source, close). Raises FeedError if none do."""
    errs = []
    for name, sym in sources:
        try:
            return name, SECONDARY_FETCH[name](sym, bar_open, now, get=get)
        except (FeedError, StopIteration, KeyError, TypeError, ValueError) as e:
            errs.append(f"{name}: {e}")
    raise FeedError("no secondary feed answered: " + "; ".join(errs))
