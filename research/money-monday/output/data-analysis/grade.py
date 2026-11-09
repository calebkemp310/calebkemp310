#!/usr/bin/env python3
"""Task 5: apply the four frozen Money Monday checks to features.csv + catalyst_labels.csv.
Run with: python3 -I grade.py

Grading code never reads max_gain. That column exists only in features.csv and is
read by analyze.py (Task 6), never here.

Writes input/data/graded.csv with columns:
  date, ticker, low_float, catalyst, former_runner, unusual_volume,
  catalyst_excluded, stale_float, grade

Frozen rules (from the pre-registered plan, copied verbatim):
  low_float:        shares_out < 90,000,000
  catalyst:         from catalyst_labels.csv: yes -> True, no -> False,
                     excluded -> None (dropped from H2 only, not from the other checks)
  former_runner:    max_runup_30 >= 0.50 AND drawdown_from_spike <= 0.50
  unusual_volume:   pm_volume >= 5 * avg_vol_30
  grade:            A = all 4 True (catalyst_excluded rows can't be graded A -
                     see note below); B = 3/4 True including catalyst; else FAIL
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FEATURES_CSV = ROOT / "input/data/features.csv"
LABELS_CSV = ROOT / "input/data/catalyst_labels.csv"
OUT_CSV = ROOT / "input/data/graded.csv"

LOW_FLOAT_MAX = 90_000_000
FORMER_RUNNER_RUNUP = 0.50
FORMER_RUNNER_DRAWDOWN_MAX = 0.50
VOLUME_MULTIPLE = 5.0


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load_labels():
    labels = {}
    if not LABELS_CSV.exists():
        return labels
    with open(LABELS_CSV, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            labels[(row["date"], row["ticker"])] = row["label"].strip().lower()
    return labels


def grade_row(feat, catalyst_label):
    shares_out = f(feat["shares_out"])
    low_float = shares_out is not None and shares_out < LOW_FLOAT_MAX

    if catalyst_label == "yes":
        catalyst = True
        catalyst_excluded = False
    elif catalyst_label == "no":
        catalyst = False
        catalyst_excluded = False
    else:
        # "excluded" or missing label entirely -> excluded from H2, treat as
        # unknown (None) here so it never silently counts as a pass or fail.
        catalyst = None
        catalyst_excluded = True

    max_runup_30 = f(feat["max_runup_30"])
    drawdown = f(feat["drawdown_from_spike"])
    former_runner = (
        max_runup_30 is not None
        and drawdown is not None
        and max_runup_30 >= FORMER_RUNNER_RUNUP
        and drawdown <= FORMER_RUNNER_DRAWDOWN_MAX
    )

    pm_volume = f(feat["pm_volume"])
    avg_vol_30 = f(feat["avg_vol_30"])
    unusual_volume = (
        pm_volume is not None
        and avg_vol_30 is not None
        and avg_vol_30 > 0
        and pm_volume >= VOLUME_MULTIPLE * avg_vol_30
    )

    stale_float = str(feat["stale_float"]).strip().lower() == "true"

    # Grade: a row with catalyst_excluded can score at most B (3 of the other
    # checks don't exist - catalyst is required for both A and B per the
    # pre-registered rule "B = 3/4 including catalyst"), so an excluded row
    # with all three of the others True is reported as FAIL for grading
    # purposes (it has no confirmed catalyst), but is NOT counted as a
    # catalyst failure in the H2 analysis - analyze.py must filter catalyst_excluded
    # rows out of H2 entirely rather than reading this grade.
    checks = [low_float, bool(catalyst), former_runner, unusual_volume]
    score = sum(1 for c in checks if c)
    if catalyst_excluded:
        grade = "FAIL"  # no confirmed catalyst -> cannot be A or B under the plan's rule
    elif score == 4:
        grade = "A"
    elif score == 3 and catalyst:
        grade = "B"
    else:
        grade = "FAIL"

    return {
        "low_float": low_float,
        "catalyst": catalyst if catalyst is not None else "",
        "former_runner": former_runner,
        "unusual_volume": unusual_volume,
        "catalyst_excluded": catalyst_excluded,
        "stale_float": stale_float,
        "grade": grade,
    }


def main():
    features = list(csv.DictReader(open(FEATURES_CSV, encoding="utf-8")))
    labels = load_labels()

    if not labels:
        print("WARNING: catalyst_labels.csv is empty or missing - all rows will be catalyst_excluded.")

    out_rows = []
    missing_labels = []
    for feat in features:
        key = (feat["date"], feat["ticker"])
        label = labels.get(key)
        if label is None:
            missing_labels.append(key)
        g = grade_row(feat, label)
        out_rows.append({"date": feat["date"], "ticker": feat["ticker"], **g})

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        fieldnames = ["date", "ticker", "low_float", "catalyst", "former_runner",
                      "unusual_volume", "catalyst_excluded", "stale_float", "grade"]
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)

    print(f"Wrote {len(out_rows)} rows to {OUT_CSV}")
    from collections import Counter
    print("Grade distribution:", Counter(r["grade"] for r in out_rows))
    print("catalyst_excluded count:", sum(1 for r in out_rows if r["catalyst_excluded"]))
    print(f"Rows with no catalyst label at all (treated as excluded): {len(missing_labels)}")
    if missing_labels:
        print("  e.g.", missing_labels[:5])


if __name__ == "__main__":
    main()
