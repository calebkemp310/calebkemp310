import numpy as np
import pytest

from agent.config import StrategyConfig
from agent.signal import decide
from agent.strategies import vol_target_trend
from tests.test_backtest import make_df

CFG = StrategyConfig()


def test_decision_equals_backtest_strategy_on_every_bar():
    df = make_df(400, seed=5)
    sig = vol_target_trend(df, n=CFG.sma_n, target=CFG.vol_target)
    for t in range(60, 400, 7):
        d = decide(df.iloc[: t + 1], CFG)
        assert d.long == bool(sig["entry"][t])
        assert d.weight == pytest.approx(min(sig["weight"][t], 1.0))
        assert 0.0 <= d.weight <= 1.0


def test_decision_ignores_future_bars():
    df = make_df(400, seed=6)
    fut = df.copy()
    fut.iloc[301:, :4] *= 0.3
    assert decide(df.iloc[:301], CFG) == decide(fut.iloc[:301], CFG)


def test_too_little_history_raises():
    with pytest.raises(ValueError):
        decide(make_df(40), CFG)
