"""Turns closed daily candles into a decision, using the SAME strategy function
the backtest used (agent.strategies.vol_target_trend). Never re-implement it here."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import indicators as ind
from .config import StrategyConfig
from .strategies import vol_target_trend


@dataclass(frozen=True)
class Decision:
    bar: pd.Timestamp     # open time of the last CLOSED daily bar
    close: float
    long: bool            # trend says hold
    weight: float         # sleeve fraction to commit on entry, 0..1 (times sleeve_cap later)
    atr: float
    sma: float
    vol: float


def decide(daily: pd.DataFrame, cfg: StrategyConfig) -> Decision:
    if len(daily) < max(cfg.sma_n, 31) + 1:
        raise ValueError(f"need more than {cfg.sma_n} closed daily bars, got {len(daily)}")
    sig = vol_target_trend(daily, n=cfg.sma_n, target=cfg.vol_target)
    long = bool(sig["entry"][-1])
    if long == bool(sig["exit"][-1]):
        raise ValueError("entry and exit both true/false: strategy contract broken")
    return Decision(
        bar=daily.index[-1],
        close=float(daily["close"].iloc[-1]),
        long=long,
        weight=float(min(max(sig["weight"][-1], 0.0), 1.0)),
        atr=float(ind.atr(daily, cfg.atr_n).iloc[-1]),
        sma=float(ind.sma(daily["close"], cfg.sma_n).iloc[-1]),
        vol=float(ind.realized_vol(daily["close"], 30, 365).iloc[-1]),
    )
