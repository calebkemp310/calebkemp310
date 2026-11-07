"""One idempotent paper-trading cycle (DESIGN.md section 5).

    python -m agent.runner --state-dir ../paper-state --outbox outbox.md [--action run|kill|rearm]

Safe to run every hour: a daily bar is acted on exactly once, missed runs are
caught up on the next one, and nothing here can reach a real exchange account.
Exit code 0 = cycle completed (including freezes); 1 = refused to run (e.g.
corrupt state), which fails the workflow and emails the repo owner.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from . import broker_paper as bk
from . import feeds
from . import state as st
from .config import FEES, LIMITS, SECONDARY, STRATEGY, Fees, Limits, StrategyConfig
from .report import write_report
from .risk import Order, RiskContext, assess, vet
from .signal import decide

ROOT = Path(__file__).resolve().parent.parent
KILL_FILE = ROOT / "KILL"


class LiveMarket:
    """Public Coinbase data + secondary cross-check. Read-only."""

    def __init__(self, get=feeds.http_get_json):
        self.get = get

    def daily(self, product, now, bars):
        return feeds.coinbase_candles(product, 86400, now, bars, get=self.get)

    def hourly(self, product, now):
        df, _ = feeds.coinbase_candles(product, 3600, now, 48, get=self.get)
        return df

    def quote(self, product):
        return feeds.coinbase_quote(product, get=self.get)

    def secondary(self, product, bar_open, now):
        return feeds.secondary_close(SECONDARY[product], bar_open, now, get=self.get)


def _h(delta: timedelta) -> float:
    return delta.total_seconds() / 3600


def _record_error(state: dict, now: datetime, L: Limits) -> list[str]:
    e = state["errors"]
    e["consecutive"] += 1
    e["recent"] = [t for t in e["recent"] if now - datetime.fromisoformat(t) < timedelta(hours=24)] + [now.isoformat()]
    if e["consecutive"] == L.max_consecutive_errors or len(e["recent"]) == L.max_errors_24h:
        return [f"Data errors: {e['consecutive']} in a row, {len(e['recent'])} in 24h. Trading is frozen until data is clean."]
    return []


def run_cycle(now: datetime, market, state_dir: Path, action: str = "run", kill_file: bool = False,
              cfg: StrategyConfig = STRATEGY, L: Limits = LIMITS, fees: Fees = FEES) -> dict:
    state_dir.mkdir(parents=True, exist_ok=True)
    sp, lp = state_dir / "state.json", state_dir / "ledger.jsonl"
    alerts: list[str] = []
    recs: list[dict] = []
    ts = now.isoformat()

    if sp.exists():
        state = st.load(sp)  # StateError propagates: refuse to act on corrupt state
    else:
        state = st.new_state(cfg.start_equity, now)
        state["last_processed_bar"] = {}
        alerts.append(f"Paper trading started: virtual ${cfg.start_equity:,.0f}, strategy SMA{cfg.sma_n} "
                      f"vol-target {cfg.vol_target:.0%}, coins {', '.join(cfg.products)}.")
    prev_success = state["last_success"]
    state["last_run"] = ts
    if prev_success and _h(now - datetime.fromisoformat(prev_success)) > L.heartbeat_gap_h:
        alerts.append(f"Heartbeat gap: no successful run since {prev_success} "
                      f"({_h(now - datetime.fromisoformat(prev_success)):.0f}h).")

    armed_before = state["armed"]
    rearmed = False
    if action == "rearm":
        if kill_file:
            alerts.append("Re-arm refused: the KILL file is still in the repo. Delete it first.")
        elif not state["armed"]:
            state["armed"], rearmed = True, True
            state.pop("kill_reason", None)
            alerts.append("Re-armed by Caleb. Peak equity resets to the current mark.")
    if action == "kill" and state["armed"]:
        state["armed"] = False
        state["kill_reason"] = "manual kill (workflow button)"

    def finish(ok: bool, prices: dict | None = None, data: dict | None = None) -> dict:
        if ok:
            state["last_success"] = ts
        st.save(state, sp)
        st.append_ledger(lp, recs)  # ledger first, so the report includes this run
        if prices is not None:
            write_report(state_dir, state, prices, data)
        if alerts:  # permanent copy of every alert, whatever happens to the issue post
            with (state_dir / "alerts.md").open("a") as f:
                f.write(f"\n## {ts[:16].replace('T', ' ')} UTC\n" + "".join(f"- {m}\n" for m in alerts))
        return {"alerts": alerts, "records": recs, "state": state}

    # ---- data ------------------------------------------------------------------
    data = {}
    try:
        for p in cfg.products:
            daily, forming_open = market.daily(p, now, cfg.daily_lookback_days)
            data[p] = {"daily": daily, "forming_open": forming_open,
                       "hourly": market.hourly(p, now), "quote": market.quote(p)}
    except feeds.FeedError as e:
        recs.append({"type": "error", "ts": ts, "error": str(e)})
        alerts += _record_error(state, now, L)
        if not state["armed"] and state["positions"]:
            alerts.append("Kill requested but prices are unavailable: positions will be flattened on the next run with data.")
        return finish(False)
    state["errors"]["consecutive"] = 0

    gaps = {}
    for p in cfg.products:
        d = data[p]["daily"]
        try:
            src, c2 = market.secondary(p, d.index[-1], now)
            gaps[p] = float(d["close"].iloc[-1]) / c2 - 1
            recs.append({"type": "crosscheck", "ts": ts, "product": p, "source": src, "gap": gaps[p]})
        except feeds.FeedError as e:
            gaps[p] = None
            recs.append({"type": "error", "ts": ts, "error": f"secondary {p}: {e}"})
            alerts += _record_error(state, now, L)

    # ---- marks and day bookkeeping ---------------------------------------------
    quotes = {p: data[p]["quote"] for p in cfg.products}
    prices = {p: (q["bid"] + q["ask"]) / 2 for p, q in quotes.items()}
    eq, sh = bk.equity(state, prices), bk.shadow_equity(state, prices)
    if rearmed:
        state["peak_equity"] = eq
    state["peak_equity"] = max(state["peak_equity"], eq)
    today = now.date().isoformat()
    new_day = state["day"] != today
    if new_day:
        state.update(day=today, day_start_equity=eq, entries_today={}, daily_loss_alerted=None)

    def context() -> RiskContext:
        pr = state["positions"]
        return RiskContext(
            now=now, armed=state["armed"], kill_file=kill_file,
            equity=bk.equity(state, prices), peak_equity=state["peak_equity"],
            day_start_equity=state["day_start_equity"],
            daily_bar_close=min(data[p]["daily"].index[-1] for p in cfg.products).to_pydatetime() + timedelta(days=1),
            hourly_bar_close=min(data[p]["hourly"].index[-1] for p in cfg.products).to_pydatetime() + timedelta(hours=1),
            feed_gaps=gaps, consecutive_errors=state["errors"]["consecutive"],
            errors_24h=len([t for t in state["errors"]["recent"]
                            if now - datetime.fromisoformat(t) < timedelta(hours=24)]),
            positions={p: v["qty"] * prices[p] for p, v in pr.items()},
            entries_today=state["entries_today"],
            last_price={p: q["price"] for p, q in quotes.items()},
        )

    ctx = context()
    v = assess(ctx, L)
    recs.append({"type": "mark", "ts": ts, "equity": eq, "shadow_equity": sh, "peak": state["peak_equity"],
                 "mode": v.mode, "reasons": v.reasons, "block_entries": v.block_entries, "prices": prices})

    def fill(order: Order, ref_open, extra=None):
        rec = bk.execute(order, quotes[order.product], state, fees, now, ref_open, prices, extra)
        recs.append(rec)
        return rec

    # ---- kill ------------------------------------------------------------------
    if v.mode == "kill":
        was_holding = list(state["positions"])
        for p, pos in list(state["positions"].items()):
            o, why = vet(Order(p, "sell", "kill", None, pos["qty"], prices[p]), ctx, L, v)
            if o:
                fill(o, None)
        state["armed"] = False
        state.setdefault("kill_reason", "; ".join(v.reasons))
        if armed_before or was_holding:
            alerts.append(f"KILL: {state['kill_reason']}. "
                          f"Flattened {len(was_holding)} position(s). Re-arm needs Caleb (workflow 'rearm').")
        recs.append({"type": "kill", "ts": ts, "reasons": v.reasons, "flattened": was_holding})
        return finish(True, prices, data)

    # ---- freeze ----------------------------------------------------------------
    if v.mode == "freeze":
        if not state["frozen"]:
            alerts.append("FROZEN (no orders): " + "; ".join(v.reasons))
        state["frozen"] = True
        recs.append({"type": "freeze", "ts": ts, "reasons": v.reasons})
        return finish(True, prices, data)
    if state["frozen"]:
        alerts.append("Unfrozen: data checks pass again.")
        state["frozen"] = False
    if v.block_entries and state["daily_loss_alerted"] != today:
        alerts.append("Daily loss limit: " + "; ".join(v.reasons))
        state["daily_loss_alerted"] = today

    # ---- orders ----------------------------------------------------------------
    orders: list[tuple[Order, float | None, dict | None]] = []
    stopping = set()
    for p, pos in state["positions"].items():
        last_hourly = float(data[p]["hourly"]["close"].iloc[-1])
        if last_hourly <= pos["stop"]:
            orders.append((Order(p, "sell", "stop", None, pos["qty"], quotes[p]["price"]), None, None))
            stopping.add(p)
            state["stopped_latch"][p] = True
            recs.append({"type": "stop", "ts": ts, "product": p, "hourly_close": last_hourly, "stop": pos["stop"]})

    lpb = state["last_processed_bar"]
    for p in cfg.products:
        try:
            d = decide(data[p]["daily"], cfg)
        except ValueError as e:  # e.g. not enough history: no decision, never a crash
            recs.append({"type": "error", "ts": ts, "error": f"{p} decision skipped: {e}"})
            if new_day:
                alerts.append(f"{p}: no decision today ({e}).")
            continue
        bar = d.bar.date().isoformat()
        if lpb.get(p) is not None and bar <= lpb[p]:
            continue  # already acted on this bar
        if lpb.get(p):
            missed = (d.bar.date() - datetime.fromisoformat(lpb[p]).date()).days - 1
            if missed > 0:
                alerts.append(f"{p}: {missed} daily bar(s) passed without a run; acted on the latest only.")
        recs.append({"type": "decision", "ts": ts, "product": p, "bar": bar, "close": d.close, "sma": d.sma,
                     "vol30": d.vol, "atr": d.atr, "long": d.long, "weight": d.weight,
                     "ref_open": data[p]["forming_open"]})
        held = p in state["positions"]
        if held and not d.long and p not in stopping:
            orders.append((Order(p, "sell", "exit", None, state["positions"][p]["qty"], quotes[p]["price"]),
                           data[p]["forming_open"], None))
        elif not held and d.long:
            if state["stopped_latch"].get(p):
                recs.append({"type": "skip", "ts": ts, "product": p, "why": "waiting for trend to reset after a stop"})
            else:
                notional = bk.equity(state, prices) * L.sleeve_cap * d.weight
                extra = {"stop": quotes[p]["price"] - L.stop_atr_mult * d.atr, "weight": d.weight, "atr": d.atr,
                         "signal_bar": bar}
                orders.append((Order(p, "buy", "entry", notional, None, quotes[p]["price"]),
                               data[p]["forming_open"], extra))
        if not d.long:
            state["stopped_latch"][p] = False
        lpb[p] = bar

    for o, ref_open, extra in orders:
        ctx = context()
        ok, why = vet(o, ctx, L, v)
        recs.append({"type": "order", "ts": ts, "product": o.product, "side": o.side, "kind": o.kind,
                     "notional": o.notional, "qty": o.qty, "approved": ok is not None, "why": why})
        if ok is None:
            alerts.append(f"Order rejected: {o.kind} {o.side} {o.product}: {why}")
            continue
        rec = fill(ok, ref_open, extra)
        if ok.side == "buy":
            state["entries_today"][o.product] = state["entries_today"].get(o.product, 0) + 1
            alerts.append(f"PAPER BUY {o.product}: ${ok.notional:,.2f} at {rec['maker_px']:,.2f} "
                          f"(stop {extra['stop']:,.2f}, size {extra['weight']:.0%} of sleeve).")
        else:
            alerts.append(f"PAPER SELL {o.product} ({o.kind}): {rec['qty']:.6f} at {rec['maker_px']:,.2f}.")

    if new_day and now.weekday() == 0:
        e2 = bk.equity(state, prices)
        alerts.append(f"Weekly summary: equity ${e2:,.2f} ({e2 / state['start_equity'] - 1:+.2%} since start), "
                      f"taker-shadow ${bk.shadow_equity(state, prices):,.2f}, positions: "
                      f"{', '.join(state['positions']) or 'none (cash)'}.")
    return finish(True, prices, data)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", required=True, type=Path)
    ap.add_argument("--outbox", type=Path)
    ap.add_argument("--action", default="run", choices=["run", "kill", "rearm"])
    a = ap.parse_args(argv)
    now = datetime.now(timezone.utc)
    try:
        out = run_cycle(now, LiveMarket(), a.state_dir, a.action, kill_file=KILL_FILE.exists())
    except st.StateError as e:
        msg = f"REFUSED TO RUN: {e}"
        if a.outbox:
            a.outbox.write_text(msg + "\n")
        print(msg, file=sys.stderr)
        return 1
    if a.outbox:
        a.outbox.write_text("".join(f"- {m}\n" for m in out["alerts"]))
    for m in out["alerts"]:
        print(m)
    print(f"cycle ok at {now.isoformat()}: {len(out['records'])} ledger records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
