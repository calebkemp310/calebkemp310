"""Performance statistics, including a multiple-testing correction.

Sharpe is computed on DAILY returns (equity resampled to UTC day closes) and
annualised with 365 days, since crypto trades every day.
"""
from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np
import pandas as pd

N = NormalDist()
EULER = 0.5772156649


def daily_returns(equity: pd.Series) -> pd.Series:
    """Equity on a daily grid. Bars longer than a day (weekly) are carried forward,
    so every timeframe is scored on the same daily clock."""
    return equity.resample("1D").last().ffill().pct_change().dropna()


def sharpe(r: pd.Series) -> float:
    sd = r.std()
    return float(r.mean() / sd * math.sqrt(365)) if sd > 0 else 0.0


def max_drawdown(equity: pd.Series) -> float:
    return float((equity / equity.cummax() - 1).min())


def cagr(equity: pd.Series) -> float:
    years = (equity.index[-1] - equity.index[0]).total_seconds() / (365.25 * 86400)
    return float((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1) if years > 0 else 0.0


def summarize(result) -> dict:
    r = daily_returns(result.equity)
    pnl = np.array([t[2] for t in result.trades])
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
    pf = float(wins.sum() / -losses.sum()) if losses.size and losses.sum() < 0 else float("inf")
    return {
        "sharpe": round(sharpe(r), 2),
        "cagr": round(cagr(result.equity), 4),
        "max_dd": round(max_drawdown(result.equity), 4),
        "trades": int(pnl.size),
        "win_rate": round(float((pnl > 0).mean()), 3) if pnl.size else None,
        "profit_factor": round(pf, 2) if math.isfinite(pf) else None,
        "exposure": round(result.exposure, 3),
        "total_return": round(float(result.equity.iloc[-1] / result.equity.iloc[0] - 1), 4),
    }


def deflated_sharpe(r: pd.Series, trial_sharpes_daily: list[float]) -> float:
    """Probability the true Sharpe > 0 after accounting for the number of trials
    (Bailey & Lopez de Prado, 2014). Inputs are NON-annualised daily Sharpes."""
    t = len(r)
    k = len(trial_sharpes_daily)
    if t < 30 or k < 2 or r.std() == 0:
        return float("nan")
    sr = r.mean() / r.std()
    var_sr = float(np.var(trial_sharpes_daily, ddof=1))
    sr0 = math.sqrt(max(var_sr, 1e-12)) * ((1 - EULER) * N.inv_cdf(1 - 1 / k) + EULER * N.inv_cdf(1 - 1 / (k * math.e)))
    skew = float(((r - r.mean()) ** 3).mean() / r.std(ddof=0) ** 3)
    kurt = float(((r - r.mean()) ** 4).mean() / r.std(ddof=0) ** 4)
    denom = math.sqrt(max(1 - skew * sr + (kurt - 1) / 4 * sr ** 2, 1e-12))
    return float(N.cdf((sr - sr0) * math.sqrt(t - 1) / denom))
