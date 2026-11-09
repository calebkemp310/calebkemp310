#!/usr/bin/env python3
"""Task 3d: build input/data/features.csv from universe.csv + the pulled bars/shares.
Run with: python3 -I features.py

Columns (per the pre-registered plan):
  date, ticker, shares_out, stale_float, pm_volume, avg_vol_30, volume_basis,
  max_runup_30, drawdown_from_spike, open, high, max_gain

Grading code (grade.py) must read every column EXCEPT max_gain. max_gain is
computed here from the same daily bar as `open`/`high` for convenience, but
kept in its own column so the grader cannot see it.
"""
import csv, json, statistics, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UNIVERSE = ROOT / "input/data/universe.csv"
BARS_DIR = ROOT / "input/data/bars"
SHARES_CSV = ROOT / "input/data/shares.csv"
OUT_CSV = ROOT / "input/data/features.csv"

MAY11 = "2026-05-11"  # uses prior_session volume fallback (pre-registered)

def load_shares():
    shares = {}
    with open(SHARES_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            shares[row["ticker"]] = row
    return shares

def load_json(path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))

def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None

def main():
    universe = list(csv.DictReader(open(UNIVERSE, encoding="utf-8")))
    shares = load_shares()

    daily_cache = {}   # date -> {"bars": {ticker: [...]}}
    pm_cache = {}       # date -> {"bars": {ticker: [...]}}

    rows_out = []
    skipped = []

    for row in universe:
        date, ticker = row["date"], row["ticker"]

        if date not in daily_cache:
            daily_cache[date] = load_json(BARS_DIR / f"d_{date}.json")
        daily = daily_cache[date]
        if daily is None:
            skipped.append((date, ticker, "no daily bars file"))
            continue
        dbars = daily["bars"].get(ticker)
        if not dbars:
            skipped.append((date, ticker, "no daily bars for ticker (invalid/delisted)"))
            continue

        # Webull daily bars come back newest-first (confirmed in build_universe/Task1 probes).
        # dbars[0] is the Monday itself; dbars[1:] are the prior sessions, most recent first.
        monday_bar = dbars[0]
        prior_bars = dbars[1:]  # up to 30 prior sessions

        o = f(monday_bar["open"])
        h = f(monday_bar["high"])
        if o is None or h is None or o == 0:
            skipped.append((date, ticker, "bad open/high on Monday bar"))
            continue
        max_gain = h / o - 1.0

        # Former runner: a +50% day in the prior 30 sessions (close/close, or high vs prior close),
        # and the latest pre-Monday close no more than 50% below that spike's high.
        max_runup_30 = None
        drawdown_from_spike = None
        if len(prior_bars) >= 2:
            runups = []
            for i in range(len(prior_bars) - 1):
                today_bar = prior_bars[i]
                prev_bar = prior_bars[i + 1]
                prev_close = f(prev_bar["close"])
                today_close = f(today_bar["close"])
                today_high = f(today_bar["high"])
                if prev_close and prev_close > 0:
                    if today_close is not None:
                        runups.append((today_close / prev_close - 1.0, today_high))
                    if today_high is not None:
                        runups.append((today_high / prev_close - 1.0, today_high))
            if runups:
                best_runup, best_spike_high = max(runups, key=lambda x: x[0])
                max_runup_30 = best_runup
                latest_pre_monday_close = f(prior_bars[0]["close"])
                if latest_pre_monday_close is not None and best_spike_high and best_spike_high > 0:
                    drawdown_from_spike = 1.0 - (latest_pre_monday_close / best_spike_high)

        # 30-day average daily volume (prior sessions only, excludes the Monday itself).
        prior_vols = [f(b["volume"]) for b in prior_bars[:30]]
        prior_vols = [v for v in prior_vols if v is not None]
        avg_vol_30 = statistics.mean(prior_vols) if prior_vols else None

        # Premarket volume: sum of PRE bars on the Monday itself, or prior_session fallback for May 11.
        pm_volume = None
        volume_basis = "premarket"
        if date == MAY11:
            volume_basis = "prior_session"
            pm_volume = prior_vols[0] if prior_vols else None
        else:
            if date not in pm_cache:
                pm_cache[date] = load_json(BARS_DIR / f"pm_{date}.json")
            pm = pm_cache[date]
            pm_bars = pm["bars"].get(ticker) if pm else None
            if pm_bars:
                vols = [f(b["volume"]) for b in pm_bars]
                pm_volume = sum(v for v in vols if v is not None)
            else:
                # No premarket bars for this ticker (shouldn't happen per the pull report,
                # but fall back honestly rather than silently zero it).
                volume_basis = "prior_session"
                pm_volume = prior_vols[0] if prior_vols else None

        share_row = shares.get(ticker)
        shares_out = f(share_row["out_standing_shares"]) if share_row else None
        fifty2_high = f(share_row["fifty_two_wk_high"]) if share_row else None

        # Stale-float flag: today's share count vs Monday's volume, or a 52-wk high that implies
        # a reverse split (price now far below a once-much-higher high is a proxy signal; the
        # precise "offering/conversion/reverse split in prior 30 days" signal isn't available from
        # share snapshots alone, so this flag is a conservative proxy, documented here).
        stale_float = False
        if shares_out and shares_out > 0 and monday_bar.get("volume"):
            monday_vol = f(monday_bar["volume"])
            if monday_vol and monday_vol > 50 * shares_out:
                stale_float = True
        if fifty2_high and o and fifty2_high > 10 * o:
            stale_float = True

        rows_out.append({
            "date": date,
            "ticker": ticker,
            "shares_out": shares_out,
            "stale_float": stale_float,
            "pm_volume": pm_volume,
            "avg_vol_30": avg_vol_30,
            "volume_basis": volume_basis,
            "max_runup_30": max_runup_30,
            "drawdown_from_spike": drawdown_from_spike,
            "open": o,
            "high": h,
            "max_gain": max_gain,
        })

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["date", "ticker", "shares_out", "stale_float", "pm_volume", "avg_vol_30",
                  "volume_basis", "max_runup_30", "drawdown_from_spike", "open", "high", "max_gain"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows_out:
            w.writerow(r)

    print(f"Wrote {len(rows_out)} rows to {OUT_CSV}")
    print(f"Skipped {len(skipped)} universe rows:")
    for s in skipped:
        print("  SKIP", s)

if __name__ == "__main__":
    main()
