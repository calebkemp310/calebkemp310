import json
from datetime import datetime, timezone

import pytest

from agent import broker_paper as bk
from agent import state as st
from agent.config import Fees
from agent.risk import Order

NOW = datetime(2026, 11, 8, 0, 7, tzinfo=timezone.utc)
F = Fees()
Q = {"bid": 100.0, "ask": 100.1}


def fresh():
    return st.new_state(10_000.0, NOW)


# ---- state / ledger ------------------------------------------------------------

def test_state_round_trip(tmp_path):
    p = tmp_path / "state.json"
    s = fresh()
    st.save(s, p)
    assert st.load(p) == s


def test_checksum_catches_edits(tmp_path):
    p = tmp_path / "state.json"
    st.save(fresh(), p)
    raw = json.loads(p.read_text())
    raw["cash"] = 1e9
    p.write_text(json.dumps(raw))
    with pytest.raises(st.StateError):
        st.load(p)


def test_truncated_state_raises(tmp_path):
    p = tmp_path / "state.json"
    st.save(fresh(), p)
    p.write_text(p.read_text()[:40])
    with pytest.raises(st.StateError):
        st.load(p)


def test_missing_state_raises(tmp_path):
    with pytest.raises(st.StateError):
        st.load(tmp_path / "nope.json")


def test_ledger_is_append_only(tmp_path):
    p = tmp_path / "ledger.jsonl"
    st.append_ledger(p, [{"a": 1}])
    first = p.read_text()
    st.append_ledger(p, [{"b": 2}, {"c": 3}])
    assert p.read_text().startswith(first)
    assert [list(r)[0] for r in st.read_ledger(p)] == ["a", "b", "c"]


# ---- paper broker --------------------------------------------------------------

def buy(notional=2_000.0):
    return Order("BTC-USD", "buy", "entry", notional, None, 100.0)


def sell(kind="exit"):
    return Order("BTC-USD", "sell", kind, None, 1.0, 100.0)


def test_buy_uses_bid_and_maker_fee():
    s = fresh()
    rec = bk.execute(buy(), Q, s, F, NOW, ref_open=99.0, prices={"BTC-USD": 100.05})
    assert rec["maker_px"] == 100.0
    assert s["positions"]["BTC-USD"]["qty"] == pytest.approx(2_000 * (1 - 0.004) / 100.0)
    assert s["cash"] == pytest.approx(8_000.0)
    assert rec["maker_gap_vs_open"] == pytest.approx(100.0 / 99.0 - 1)


def test_shadow_uses_ask_slip_and_taker_fee():
    s = fresh()
    bk.execute(buy(), Q, s, F, NOW, ref_open=None, prices={"BTC-USD": 100.05})
    sq = s["shadow"]["positions"]["BTC-USD"]["qty"]
    assert sq == pytest.approx(2_000 * (1 - 0.009) / (100.1 * 1.0005))


def test_round_trip_reconciles():
    s = fresh()
    bk.execute(buy(), Q, s, F, NOW, None, {"BTC-USD": 100.05})
    qty = s["positions"]["BTC-USD"]["qty"]
    rec = bk.execute(sell(), Q, s, F, NOW, None, {"BTC-USD": 100.05})
    assert "BTC-USD" not in s["positions"] and "BTC-USD" not in s["shadow"]["positions"]
    assert s["cash"] == pytest.approx(8_000 + qty * 100.1 * (1 - 0.004))
    assert rec["proceeds"] == pytest.approx(qty * 100.1 * 0.996)
    assert s["shadow"]["cash"] < s["cash"]  # taker book always pays more


def test_equity_marks():
    s = fresh()
    bk.execute(buy(), Q, s, F, NOW, None, {"BTC-USD": 100.05})
    qty = s["positions"]["BTC-USD"]["qty"]
    assert bk.equity(s, {"BTC-USD": 110.0}) == pytest.approx(8_000 + qty * 110.0)


def test_broker_rejects_bad_inputs():
    s = fresh()
    with pytest.raises(bk.BrokerError):
        bk.execute(sell(), Q, s, F, NOW, None, {})          # nothing to sell
    with pytest.raises(bk.BrokerError):
        bk.execute(buy(notional=0.0), Q, s, F, NOW, None, {"BTC-USD": 100.0})
    with pytest.raises(bk.BrokerError):
        bk.execute(buy(notional=20_000.0), Q, s, F, NOW, None, {"BTC-USD": 100.0})  # more than cash
    with pytest.raises(bk.BrokerError):
        bk.execute(buy(), {"bid": 101.0, "ask": 100.0}, s, F, NOW, None, {"BTC-USD": 100.0})  # crossed quote
