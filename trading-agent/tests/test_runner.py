import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from agent import feeds
from agent import runner as rn
from agent import state as st
from agent.config import Limits, StrategyConfig
from agent.report import expected_trade_days, tracking

CFG = StrategyConfig(products=("BTC-USD", "ETH-USD"), daily_lookback_days=150)
L = Limits()
START = pd.Timestamp("2026-01-01", tz="UTC")


def path_prices(kind: str, n=400, seed=0):
    rng = np.random.default_rng(seed)
    if kind == "up_then_down":   # long trend up, then a sharp break
        drift = np.r_[np.full(200, 0.006), np.full(60, -0.02), np.full(n - 260, 0.006)]
    elif kind == "random":
        drift = rng.normal(0.0005, 0.0, n)
    else:
        drift = np.full(n, 0.004)
    r = drift + rng.normal(0, 0.012 if kind != "random" else 0.03, n)
    return 100 * np.exp(np.cumsum(r))


def make_daily(close):
    idx = pd.date_range(START, periods=len(close), freq="1D")
    open_ = np.r_[close[0], close[:-1]]
    hi = np.maximum(open_, close) * 1.005
    lo = np.minimum(open_, close) * 0.995
    return pd.DataFrame({"open": open_, "high": hi, "low": lo, "close": close, "volume": 1.0}, index=idx)


class FakeMarket:
    def __init__(self, dailies: dict):
        self.dailies = dailies
        self.fail = False
        self.secondary_gap = {}
        self.secondary_down = False
        self.hourly_lag_h = 0
        self.hourly_close = {}   # product -> override for the last hourly close

    def _check(self):
        if self.fail:
            raise feeds.FeedError("simulated outage")

    def daily(self, p, now, bars):
        self._check()
        d = self.dailies[p]
        closed = d[d.index + pd.Timedelta(days=1) <= now]
        forming = d[(d.index <= now) & (d.index + pd.Timedelta(days=1) > now)]
        return closed.tail(bars), float(forming["open"].iloc[-1]) if len(forming) else float(closed["close"].iloc[-1])

    def hourly(self, p, now):
        self._check()
        end = pd.Timestamp(now).floor("1h") - pd.Timedelta(hours=1 + self.hourly_lag_h)
        idx = pd.date_range(end=end, periods=48, freq="1h")
        px = self.quote(p)["price"]
        c = np.full(48, px)
        if p in self.hourly_close:
            c[-1] = self.hourly_close[p]
        return pd.DataFrame({"open": c, "high": c, "low": c, "close": c, "volume": 1.0}, index=idx)

    def quote(self, p):
        self._check()
        _, fo = self.daily(p, self.now, 5)
        return {"bid": fo * 0.9999, "ask": fo * 1.0001, "price": fo, "time": None}

    def secondary(self, p, bar_open, now):
        if self.secondary_down:
            raise feeds.FeedError("secondary down")
        c = float(self.dailies[p].loc[bar_open, "close"])
        return "fake", c / (1 + self.secondary_gap.get(p, 0.0))


def at(day: int, hour=0, minute=7):
    return (START + pd.Timedelta(days=day, hours=hour, minutes=minute)).to_pydatetime()


def run(m, now, tmp, **kw):
    m.now = now
    return rn.run_cycle(now, m, tmp, cfg=CFG, L=kw.pop("L", L), **kw)


def mkt(kind="up_then_down", seed=0):
    return FakeMarket({"BTC-USD": make_daily(path_prices(kind, seed=seed)),
                       "ETH-USD": make_daily(path_prices(kind, seed=seed + 1))})


def kinds(out, t):
    return [r for r in out["records"] if r["type"] == t]


# ---- lifecycle -------------------------------------------------------------------

def test_first_run_creates_state_and_enters_uptrend(tmp_path):
    m = mkt()
    out = run(m, at(120), tmp_path)
    assert (tmp_path / "state.json").exists() and (tmp_path / "report.md").exists()
    assert any("started" in a for a in out["alerts"])
    fills = kinds(out, "fill")
    assert {f["product"] for f in fills} == {"BTC-USD", "ETH-USD"}
    s = out["state"]
    for p, pos in s["positions"].items():
        notional = pos["qty"] * pos["entry_px"] / (1 - 0.004)
        assert notional <= 0.25 * 10_000 + 1e-6
        assert pos["stop"] < pos["entry_px"]


def test_same_bar_is_acted_on_once(tmp_path):
    m = mkt()
    run(m, at(120), tmp_path)
    out = run(m, at(120, hour=1), tmp_path)
    assert kinds(out, "decision") == [] and kinds(out, "fill") == []


def test_catch_up_after_missed_runs(tmp_path):
    m = mkt()
    run(m, at(120), tmp_path)
    out = run(m, at(124), tmp_path)
    assert len(kinds(out, "decision")) == 2  # one per coin, latest bar only
    assert any("3 daily bar(s) passed" in a for a in out["alerts"])


def test_exit_when_trend_breaks(tmp_path):
    m = mkt()
    run(m, at(150), tmp_path)
    exited = False
    for day in range(151, 260):
        out = run(m, at(day), tmp_path, L=replace(L, stop_atr_mult=1e9))
        if any(f["side"] == "sell" and f["kind"] == "exit" for f in kinds(out, "fill")):
            exited = True
            break
    assert exited


def test_heartbeat_gap_alert(tmp_path):
    m = mkt()
    run(m, at(120), tmp_path)
    out = run(m, at(122), tmp_path)
    assert any("Heartbeat gap" in a for a in out["alerts"])


# ---- kill switch -----------------------------------------------------------------

def test_kill_file_flattens_and_disarms(tmp_path):
    m = mkt()
    run(m, at(120), tmp_path)
    out = run(m, at(120, hour=2), tmp_path, kill_file=True)
    assert out["state"]["positions"] == {} and out["state"]["armed"] is False
    assert {f["kind"] for f in kinds(out, "fill")} == {"kill"}
    assert any(a.startswith("KILL") for a in out["alerts"])
    again = run(m, at(120, hour=3), tmp_path, kill_file=True)
    assert not any(a.startswith("KILL") for a in again["alerts"])  # no hourly spam
    assert kinds(again, "fill") == []


def test_manual_kill_then_rearm(tmp_path):
    m = mkt()
    run(m, at(120), tmp_path)
    out = run(m, at(120, hour=2), tmp_path, action="kill")
    assert out["state"]["armed"] is False and out["state"]["positions"] == {}
    refused = run(m, at(120, hour=3), tmp_path, action="rearm", kill_file=True)
    assert refused["state"]["armed"] is False and any("refused" in a for a in refused["alerts"])
    ok = run(m, at(120, hour=4), tmp_path, action="rearm")
    assert ok["state"]["armed"] is True


def test_drawdown_kill(tmp_path):
    m = mkt()
    run(m, at(120), tmp_path)
    s = st.load(tmp_path / "state.json")
    s["peak_equity"] = 20_000.0
    st.save(s, tmp_path / "state.json")
    out = run(m, at(120, hour=1), tmp_path)
    assert out["state"]["armed"] is False and out["state"]["positions"] == {}
    assert "drawdown" in out["state"]["kill_reason"]


# ---- freeze / data ---------------------------------------------------------------

def test_stale_hourly_freezes_without_orders(tmp_path):
    m = mkt()
    m.hourly_lag_h = 3
    out = run(m, at(120), tmp_path)
    assert kinds(out, "fill") == [] and out["state"]["frozen"] is True
    assert any("FROZEN" in a for a in out["alerts"])
    m.hourly_lag_h = 0
    out = run(m, at(120, hour=1), tmp_path)
    assert any("Unfrozen" in a for a in out["alerts"]) and kinds(out, "fill")


def test_feed_disagreement_freezes(tmp_path):
    m = mkt()
    m.secondary_gap = {"BTC-USD": 0.05}
    out = run(m, at(120), tmp_path)
    assert kinds(out, "fill") == [] and out["state"]["frozen"]


def test_outage_counts_errors_then_freezes(tmp_path):
    m = mkt()
    run(m, at(120), tmp_path)
    m.fail = True
    alerts = []
    for h in range(1, 4):
        alerts += run(m, at(120, hour=h), tmp_path)["alerts"]
    assert any("Data errors: 3 in a row" in a for a in alerts)
    s = st.load(tmp_path / "state.json")
    assert s["errors"]["consecutive"] == 3 and s["last_success"] == at(120).isoformat()


def test_secondary_down_is_counted_not_frozen(tmp_path):
    m = mkt()
    m.secondary_down = True
    out = run(m, at(120), tmp_path)
    assert kinds(out, "fill")  # one run with no cross-check still trades...
    assert out["state"]["errors"]["consecutive"] == 2  # ...but both misses count toward the budget


def test_corrupt_state_refuses(tmp_path):
    m = mkt()
    run(m, at(120), tmp_path)
    p = tmp_path / "state.json"
    raw = json.loads(p.read_text())
    raw["cash"] = 999_999
    p.write_text(json.dumps(raw))
    with pytest.raises(st.StateError):
        run(m, at(120, hour=1), tmp_path)


def test_cli_returns_1_on_corrupt_state(tmp_path):
    (tmp_path / "state.json").write_text("{not json")
    box = tmp_path / "outbox.md"
    assert rn.main(["--state-dir", str(tmp_path), "--outbox", str(box)]) == 1
    assert "REFUSED" in box.read_text()


# ---- limits in the loop ------------------------------------------------------------

def test_daily_loss_blocks_entry(tmp_path):
    m = mkt()
    run(m, at(30), tmp_path)  # too early for SMA50: no decisions possible yet...
    s = st.load(tmp_path / "state.json")
    s.update(day=at(120).date().isoformat(), day_start_equity=11_000.0)
    st.save(s, tmp_path / "state.json")
    out = run(m, at(120), tmp_path)
    assert kinds(out, "fill") == []
    assert any("Daily loss limit" in a for a in out["alerts"])
    assert all(not o["approved"] for o in kinds(out, "order"))


def test_catastrophe_stop_and_latch(tmp_path):
    m = mkt()
    run(m, at(120), tmp_path)
    stop = st.load(tmp_path / "state.json")["positions"]["BTC-USD"]["stop"]
    m.hourly_close = {"BTC-USD": stop * 0.99}
    out = run(m, at(120, hour=1), tmp_path)
    assert [f["kind"] for f in kinds(out, "fill")] == ["stop"]
    m.hourly_close = {}
    out = run(m, at(121), tmp_path)  # trend still up: latch blocks re-entry
    assert "BTC-USD" not in out["state"]["positions"]
    assert any(r["type"] == "skip" and r["product"] == "BTC-USD" for r in out["records"])


# ---- tracking: paper == backtest on the same candles ------------------------------

@pytest.mark.parametrize("seed", [3, 11])
def test_replay_matches_backtest_trade_days(tmp_path, seed):
    m = FakeMarket({"BTC-USD": make_daily(path_prices("random", seed=seed)),
                    "ETH-USD": make_daily(path_prices("random", seed=seed + 50))})
    loose = replace(L, stop_atr_mult=1e9, drawdown_kill=-0.99, daily_loss_block=-0.99)
    data = None
    for day in range(60, 260):
        out = run(m, at(day), tmp_path, L=loose)
    m.now = at(259)
    data = {p: {"daily": m.daily(p, at(259), 400)[0]} for p in CFG.products}
    t = tracking(tmp_path, data)
    for p in CFG.products:
        assert t[p]["expected"], "replay should produce trades"
        assert t[p]["actual"] == t[p]["expected"], p
        assert t[p]["match"] is True
