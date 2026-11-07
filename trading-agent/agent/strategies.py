"""Candidate strategies. Signals only; execution and sizing live elsewhere.

Each strategy returns {'entry', 'exit'[, 'max_hold']} boolean arrays computed at
bar close. GRIDS lists the parameter neighbourhood swept for each one; every
point counts as a trial in the deflated-Sharpe test.
"""
from __future__ import annotations

import itertools

import pandas as pd

from . import indicators as ind


def trend_sma(df: pd.DataFrame, n: int) -> dict:
    """Long while close > SMA(n). Edge: crypto trends persist (slow capital, herding)."""
    above = df["close"] > ind.sma(df["close"], n)
    return {"entry": above.to_numpy(), "exit": (~above).to_numpy()}


def tsmom(df: pd.DataFrame, lookback: int) -> dict:
    """Time-series momentum: long while the trailing `lookback`-bar return is positive."""
    mom = df["close"].pct_change(lookback)
    up = mom > 0
    return {"entry": up.to_numpy(), "exit": (~up).fillna(True).to_numpy()}


def donchian(df: pd.DataFrame, entry_n: int, exit_n: int) -> dict:
    """Breakout: buy a close above the prior entry_n-bar high, sell a close below the prior exit_n-bar low."""
    hi = ind.prior_high(df["high"], entry_n)
    lo = ind.prior_low(df["low"], exit_n)
    return {"entry": (df["close"] > hi).to_numpy(), "exit": (df["close"] < lo).to_numpy()}


def rsi2_dip(df: pd.DataFrame, threshold: float, trend_n: int = 200, hold: int = 10) -> dict:
    """Buy short-term oversold (RSI2 < threshold) only in an uptrend; exit on close > SMA5 or after `hold` bars."""
    c = df["close"]
    uptrend = c > ind.sma(c, trend_n)
    r = ind.rsi(c, 2)
    return {
        "entry": (uptrend & (r < threshold)).to_numpy(),
        "exit": (c > ind.sma(c, 5)).to_numpy(),
        "max_hold": hold,
    }


def bollinger_revert(df: pd.DataFrame, k: float, n: int = 20, trend_n: int = 200, hold: int = 12) -> dict:
    """Buy a close below the lower band (mean - k*sd) in an uptrend; exit at the mid band or after `hold` bars."""
    c = df["close"]
    mid = ind.sma(c, n)
    sd = c.rolling(n, min_periods=n).std()
    uptrend = c > ind.sma(c, trend_n)
    return {
        "entry": (uptrend & (c < mid - k * sd)).to_numpy(),
        "exit": (c > mid).to_numpy(),
        "max_hold": hold,
    }


def _grid(**axes):
    keys = list(axes)
    return [dict(zip(keys, v)) for v in itertools.product(*axes.values())]


# name -> (function, timeframe, parameter grid). Grids are ordered so neighbours sit next to each other.
CANDIDATES = {
    "trend_sma": (trend_sma, "1d", _grid(n=[20, 30, 50, 75, 100, 150, 200])),
    "tsmom": (tsmom, "1d", _grid(lookback=[14, 30, 60, 90, 120, 180])),
    "donchian": (donchian, "1d", [p for p in _grid(entry_n=[20, 40, 55, 80, 100], exit_n=[10, 20, 30])
                                  if p["exit_n"] < p["entry_n"]]),
    "rsi2_dip": (rsi2_dip, "1d", _grid(threshold=[5, 10, 15, 20, 25])),
    "bollinger_revert_4h": (bollinger_revert, "4h", _grid(k=[1.5, 2.0, 2.5, 3.0])),
}
