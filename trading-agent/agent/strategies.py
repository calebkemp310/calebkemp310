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


# ---------------------------------------------------------------------------
# Round 2 (widened search). Pre-registered 2026-11-07 before any round-2 run.
# Every grid point below adds to the trial count used by the deflated Sharpe.
# ---------------------------------------------------------------------------

def trend_band(df: pd.DataFrame, n: int, band: float) -> dict:
    """Trend filter with a buffer: enter above SMA*(1+band), exit below SMA*(1-band).
    Same edge as trend_sma; the band exists to cut whipsaw trades and fees."""
    m = ind.sma(df["close"], n)
    return {"entry": (df["close"] > m * (1 + band)).to_numpy(),
            "exit": (df["close"] < m * (1 - band)).to_numpy()}


def vol_target_trend(df: pd.DataFrame, n: int, target: float) -> dict:
    """trend_sma sized by volatility targeting: weight = min(1, target / 30-day realized vol),
    fixed at entry. Same edge, less exposure when the coin is wild."""
    sig = trend_sma(df, n)
    vol = ind.realized_vol(df["close"], 30, 365)
    sig["weight"] = (target / vol).clip(upper=1.0).fillna(0.0).to_numpy()
    return sig


def btc_regime_trend(df: pd.DataFrame, n: int, btc_close: pd.Series, btc_n: int = 200) -> dict:
    """Own trend AND Bitcoin above its 200-day average. Edge: alt coins rarely trend up
    while BTC is in a downtrend (BTC sets the market's risk appetite)."""
    btc_up = (btc_close > ind.sma(btc_close, btc_n)).reindex(df.index).fillna(False)
    above = df["close"] > ind.sma(df["close"], n)
    return {"entry": (above & btc_up).to_numpy(), "exit": (~above | ~btc_up).to_numpy()}


btc_regime_trend.needs_btc = True


def squeeze_breakout(df: pd.DataFrame, pct: float, lookback: int = 20, exit_n: int = 10) -> dict:
    """Volatility compression then breakout: 20-day vol in its bottom `pct` of the last
    365 days AND a close above the prior 20-day high. Edge: volatility clusters, and
    quiet ranges tend to resolve in a sharp move that late buyers chase."""
    vol = ind.realized_vol(df["close"], lookback, 365)
    rank = vol.rolling(365, min_periods=365).apply(lambda x: (x <= x[-1]).mean(), raw=True)
    quiet = rank.shift(1) <= pct  # quiet BEFORE the breakout bar
    hi = ind.prior_high(df["high"], lookback)
    lo = ind.prior_low(df["low"], exit_n)
    return {"entry": (quiet & (df["close"] > hi)).to_numpy(), "exit": (df["close"] < lo).to_numpy()}


CANDIDATES_R2 = {
    "trend_band": (trend_band, "1d", _grid(n=[50, 100, 200], band=[0.02, 0.05, 0.10])),
    "weekly_trend": (trend_sma, "1w", _grid(n=[10, 20, 30, 40])),
    "vol_target_trend": (vol_target_trend, "1d", _grid(n=[50, 100, 150], target=[0.3, 0.5])),
    "btc_regime_trend": (btc_regime_trend, "1d", _grid(n=[30, 50, 100])),
    "squeeze_breakout": (squeeze_breakout, "1d", _grid(pct=[0.2, 0.3, 0.5])),
}
