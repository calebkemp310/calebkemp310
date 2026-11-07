"""Indicators. Every value at index t uses only bars 0..t (no centered windows)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def rsi(s: pd.Series, n: int) -> pd.Series:
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(100.0).where(up.notna())


def atr(df: pd.DataFrame, n: int) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def prior_high(s: pd.Series, n: int) -> pd.Series:
    """Highest value of the n bars BEFORE t (excludes t)."""
    return s.shift(1).rolling(n, min_periods=n).max()


def prior_low(s: pd.Series, n: int) -> pd.Series:
    return s.shift(1).rolling(n, min_periods=n).min()


def realized_vol(close: pd.Series, n: int, periods_per_year: float) -> pd.Series:
    return np.log(close).diff().rolling(n, min_periods=n).std() * np.sqrt(periods_per_year)
