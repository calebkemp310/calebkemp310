"""Historical candle loader.

Source: Binance public market-data mirror (data-api.binance.vision), spot klines.
Research only. Binance.com does not serve US residents, so live trading targets a
US venue (see SPEC.md); Binance history stands in for the deeper USD market.

Every bar is stamped with its OPEN time and is only used after it CLOSES.
The loader drops the still-forming last bar so a backtest never sees it.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

BASE = "https://data-api.binance.vision/api/v3/klines"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INTERVAL_MS = {"1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}


def _get(url: str, retries: int = 4) -> list:
    delay = 2.0
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return json.loads(resp.read())
        except Exception:
            if attempt == retries:
                raise
            time.sleep(delay)
            delay *= 2
    return []


def fetch_klines(symbol: str, interval: str, start: str, end: str | None = None) -> pd.DataFrame:
    """Download closed klines in [start, end). Pages 1000 bars per request."""
    step = INTERVAL_MS[interval]
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    now_ms = int(time.time() * 1000)
    end_ms = int(pd.Timestamp(end, tz="UTC").timestamp() * 1000) if end else now_ms
    rows: list = []
    cursor = start_ms
    while cursor < end_ms:
        url = f"{BASE}?symbol={symbol}&interval={interval}&startTime={cursor}&endTime={end_ms - 1}&limit=1000"
        batch = _get(url)
        if not batch:
            break
        rows.extend(batch)
        cursor = batch[-1][0] + step
    df = pd.DataFrame(rows, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_base", "taker_quote", "ignore",
    ])
    df = df[["open_time", "open", "high", "low", "close", "volume", "close_time"]]
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    # Drop any bar that has not closed yet (close_time in the future).
    df = df[df["close_time"] < now_ms]
    df = df.drop_duplicates("open_time").sort_values("open_time")
    df.index = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df.index.name = "time"
    return df[["open", "high", "low", "close", "volume"]]


def load(symbol: str, interval: str, start: str = "2019-01-01", end: str | None = None,
         refresh: bool = False) -> pd.DataFrame:
    """Load from the local cache, downloading if missing."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tag = end or "latest"
    path = DATA_DIR / f"{symbol}_{interval}_{start}_{tag}.csv"
    if path.exists() and not refresh:
        df = pd.read_csv(path, index_col="time", parse_dates=["time"])
    else:
        df = fetch_klines(symbol, interval, start, end)
        df.to_csv(path)
    validate(df, interval)
    return df


def validate(df: pd.DataFrame, interval: str) -> None:
    """Fail loudly on data that would corrupt a backtest."""
    if df.empty:
        raise ValueError("no data")
    if not df.index.is_monotonic_increasing or df.index.has_duplicates:
        raise ValueError("timestamps not strictly increasing")
    bad = (df["high"] < df[["open", "close"]].max(axis=1)) | (df["low"] > df[["open", "close"]].min(axis=1))
    if bad.any():
        raise ValueError(f"{int(bad.sum())} bars with high/low outside open/close")
    if (df[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("non-positive prices")


def fingerprint(df: pd.DataFrame) -> str:
    """Short hash of the candles, recorded with every result for reproducibility."""
    return hashlib.sha256(pd.util.hash_pandas_object(df, index=True).values.tobytes()).hexdigest()[:16]


def gap_count(df: pd.DataFrame, interval: str) -> int:
    step = pd.Timedelta(milliseconds=INTERVAL_MS[interval])
    return int((df.index.to_series().diff().dropna() > step).sum())
