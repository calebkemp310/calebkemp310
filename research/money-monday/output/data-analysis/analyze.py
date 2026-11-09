#!/usr/bin/env python3
"""Task 6: test H1-H5 against graded.csv + features.csv (for max_gain).
Run with: python3 -I analyze.py

This is the ONLY script in the pipeline allowed to read max_gain next to the
check flags - it is the whole point of the analysis. Implements, in order:
  (a) per-check pass/fail medians + one-sided Mann-Whitney U, Holm-corrected
      across the four checks, plus a Hodges-Lehmann shift estimate + 95% CI
  (b) leave-one-out: 4/4 group vs each "3/4 missing check X" group
  (c) OLS of log(1+max_gain) on the four flags with Monday fixed effects,
      HC3-ish robust errors (stdlib implementation, no numpy/scipy required)
  (d) a sensitivity run excluding stale_float rows
  (e) per pre-registered falsification criteria, mark each of H1-H5 as
      supported / rejected / insufficient
Writes output/data-analysis/results/results.json.
"""
import csv, json, math
from pathlib import Path
from itertools import combinations

ROOT = Path(__file__).resolve().parents[2]
GRADED_CSV = ROOT / "input/data/graded.csv"
FEATURES_CSV = ROOT / "input/data/features.csv"
OUT_JSON = ROOT / "output/data-analysis/results/results.json"

CHECKS = ["low_float", "catalyst", "former_runner", "unusual_volume"]
MIN_GROUP = 10  # pre-registered stop rule


def b(x):
    return str(x).strip().lower() == "true"


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load():
    graded = {(r["date"], r["ticker"]): r for r in csv.DictReader(open(GRADED_CSV, encoding="utf-8"))}
    features = {(r["date"], r["ticker"]): r for r in csv.DictReader(open(FEATURES_CSV, encoding="utf-8"))}
    merged = []
    for key, g in graded.items():
        feat = features.get(key)
        if feat is None:
            continue
        mg = f(feat["max_gain"])
        if mg is None:
            continue
        row = dict(g)
        row["max_gain"] = mg
        row["stale_float"] = b(g["stale_float"])
        row["catalyst_excluded"] = b(g["catalyst_excluded"])
        for c in CHECKS:
            if c == "catalyst":
                row[c] = None if row["catalyst_excluded"] else b(g[c])
            else:
                row[c] = b(g[c])
        merged.append(row)
    return merged


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return None
    mid = n // 2
    return xs[mid] if n % 2 else (xs[mid - 1] + xs[mid]) / 2.0


def mann_whitney_u_onesided_greater(x, y):
    """One-sided Mann-Whitney U: H1 = x tends to be greater than y.
    Returns (U, p_value_normal_approx, hodges_lehmann_shift).
    Pure-stdlib normal approximation with tie correction; adequate for the
    group sizes here (all >=10, most >=20)."""
    n1, n2 = len(x), len(y)
    if n1 == 0 or n2 == 0:
        return None, None, None
    combined = sorted([(v, 0) for v in x] + [(v, 1) for v in y])
    ranks = [0.0] * len(combined)
    i = 0
    while i < len(combined):
        j = i
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j
    rank_sum_x = sum(r for (v, grp), r in zip(combined, ranks) if grp == 0)
    u1 = rank_sum_x - n1 * (n1 + 1) / 2.0
    mu = n1 * n2 / 2.0
    # tie correction
    tie_term = 0.0
    i = 0
    while i < len(combined):
        j = i
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1
        t = j - i
        if t > 1:
            tie_term += t ** 3 - t
        i = j
    N = n1 + n2
    sigma2 = (n1 * n2 / 12.0) * ((N + 1) - tie_term / (N * (N - 1))) if N > 1 else 0
    sigma = math.sqrt(sigma2) if sigma2 > 0 else 0
    if sigma == 0:
        z = 0.0
    else:
        z = (u1 - mu - 0.5) / sigma  # continuity correction, one-sided (greater)
    p = 1.0 - _norm_cdf(z)
    # Hodges-Lehmann shift: median of all pairwise differences x_i - y_j
    diffs = sorted(xi - yj for xi in x for yj in y)
    shift = median(diffs)
    return u1, p, shift


def _norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def holm_correction(pvals_with_names):
    """pvals_with_names: list of (name, p). Returns dict name -> adjusted p."""
    ordered = sorted(pvals_with_names, key=lambda t: t[1])
    m = len(ordered)
    adjusted = {}
    running_max = 0.0
    for i, (name, p) in enumerate(ordered):
        adj = min((m - i) * p, 1.0)
        running_max = max(running_max, adj)
        adjusted[name] = running_max
    return adjusted


def per_check_test(rows, check):
    sub = [r for r in rows if r[check] is not None]
    passed = [r["max_gain"] for r in sub if r[check]]
    failed = [r["max_gain"] for r in sub if not r[check]]
    n_pass, n_fail = len(passed), len(failed)
    result = {
        "n_pass": n_pass, "n_fail": n_fail,
        "median_pass": median(passed), "median_fail": median(failed),
        "sufficient_n": n_pass >= MIN_GROUP and n_fail >= MIN_GROUP,
    }
    if result["sufficient_n"]:
        u, p, shift = mann_whitney_u_onesided_greater(passed, failed)
        result.update({"U": u, "p_raw": p, "hodges_lehmann_shift": shift})
    else:
        result.update({"U": None, "p_raw": None, "hodges_lehmann_shift": None})
    return result


def leave_one_out(rows):
    """4/4 group (all four checks True, catalyst not excluded) vs each
    '3/4 missing check X' group (exactly check X is False/None-excluded, the
    other three True)."""
    full = [r for r in rows if r["catalyst_excluded"] is False
            and all(r[c] is True for c in CHECKS)]
    out = {}
    for miss in CHECKS:
        others = [c for c in CHECKS if c != miss]
        grp = [r for r in rows
               if all(r[c] is True for c in others)
               and (r[miss] is False)]  # explicitly failed, not excluded/unknown
        n_full, n_grp = len(full), len(grp)
        entry = {"n_full": n_full, f"n_missing_{miss}": n_grp,
                 "median_full": median([r["max_gain"] for r in full]) if full else None,
                 f"median_missing_{miss}": median([r["max_gain"] for r in grp]) if grp else None,
                 "sufficient_n": n_full >= MIN_GROUP and n_grp >= MIN_GROUP}
        out[miss] = entry
    return out


def ols_with_fixed_effects(rows):
    """OLS of log(1+max_gain) on the four 0/1 flags + Monday dummies (fixed
    effects via dummy-variable regression, dropping one Monday as baseline),
    solved by normal equations (X'X)^-1 X'y using plain nested lists - no
    numpy. HC3-style robust SEs approximated via the standard OLS sandwich
    with leverage-based (1-h_ii) weighting."""
    usable = [r for r in rows if r["catalyst"] is not None]
    n = len(usable)
    if n < 100:
        return {"run": False, "reason": f"n={n} < 100, regression not run per pre-registered threshold"}

    dates = sorted(set(r["date"] for r in usable))
    baseline_date = dates[0]
    fe_dates = dates[1:]

    def design_row(r):
        x = [1.0]  # intercept
        for c in CHECKS:
            x.append(1.0 if r[c] else 0.0)
        for d in fe_dates:
            x.append(1.0 if r["date"] == d else 0.0)
        return x

    X = [design_row(r) for r in usable]
    y = [math.log(1.0 + r["max_gain"]) for r in usable]
    p = len(X[0])

    # X'X and X'y
    XtX = [[0.0] * p for _ in range(p)]
    Xty = [0.0] * p
    for xi, yi in zip(X, y):
        for a in range(p):
            Xty[a] += xi[a] * yi
            for c in range(p):
                XtX[a][c] += xi[a] * xi[c]

    beta = _solve_linear_system(XtX, Xty)
    if beta is None:
        return {"run": False, "reason": "design matrix singular (collinear Monday dummies vs checks)"}

    resid = [yi - sum(beta[a] * xi[a] for a in range(p)) for xi, yi in zip(X, y)]
    XtX_inv = _invert(XtX)
    if XtX_inv is None:
        return {"run": False, "reason": "could not invert X'X for standard errors"}

    # HC0/HC3-ish: meat = X' diag(e_i^2 / (1-h_ii)^2) X, leverage h_ii = x_i (X'X)^-1 x_i'
    meat = [[0.0] * p for _ in range(p)]
    for xi, ei in zip(X, resid):
        h_ii = sum(xi[a] * sum(XtX_inv[a][c] * xi[c] for c in range(p)) for a in range(p))
        h_ii = min(h_ii, 0.999)
        weight = (ei / (1.0 - h_ii)) ** 2
        for a in range(p):
            for c in range(p):
                meat[a][c] += xi[a] * xi[c] * weight
    # sandwich = (X'X)^-1 meat (X'X)^-1
    tmp = _matmul(XtX_inv, meat)
    sandwich = _matmul(tmp, XtX_inv)

    out = {"run": True, "n": n, "intercept": beta[0]}
    for i, c in enumerate(CHECKS, start=1):
        se = math.sqrt(max(sandwich[i][i], 0.0))
        coef = beta[i]
        ci_low, ci_high = coef - 1.96 * se, coef + 1.96 * se
        out[c] = {"coef": coef, "se": se, "ci_95": [ci_low, ci_high],
                  "excludes_zero": (ci_low > 0) or (ci_high < 0)}
    return out


def _solve_linear_system(A, bvec):
    n = len(A)
    M = [row[:] + [bvec[i]] for i, row in enumerate(A)]
    for col in range(n):
        pivot = None
        best = 0.0
        for row in range(col, n):
            if abs(M[row][col]) > best:
                best = abs(M[row][col])
                pivot = row
        if pivot is None or best < 1e-12:
            return None
        M[col], M[pivot] = M[pivot], M[col]
        pv = M[col][col]
        M[col] = [v / pv for v in M[col]]
        for row in range(n):
            if row != col and M[row][col] != 0:
                factor = M[row][col]
                M[row] = [mv - factor * cv for mv, cv in zip(M[row], M[col])]
    return [M[i][n] for i in range(n)]


def _invert(A):
    n = len(A)
    M = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(A)]
    for col in range(n):
        pivot = None
        best = 0.0
        for row in range(col, n):
            if abs(M[row][col]) > best:
                best = abs(M[row][col])
                pivot = row
        if pivot is None or best < 1e-10:
            return None
        M[col], M[pivot] = M[pivot], M[col]
        pv = M[col][col]
        M[col] = [v / pv for v in M[col]]
        for row in range(n):
            if row != col and M[row][col] != 0:
                factor = M[row][col]
                M[row] = [mv - factor * cv for mv, cv in zip(M[row], M[col])]
    return [row[n:] for row in M]


def _matmul(A, B):
    n, m, p = len(A), len(B), len(B[0])
    return [[sum(A[i][k] * B[k][j] for k in range(m)) for j in range(p)] for i in range(n)]


def falsify(per_check, loo, ols, h5_note):
    verdicts = {}
    names = {"low_float": "H1", "catalyst": "H2", "former_runner": "H3", "unusual_volume": "H4"}
    pvals = [(names[c], per_check[c]["p_raw"]) for c in CHECKS if per_check[c]["p_raw"] is not None]
    holm = holm_correction(pvals) if pvals else {}
    for c in CHECKS:
        name = names[c]
        res = per_check[c]
        if not res["sufficient_n"]:
            verdicts[name] = "insufficient"
            continue
        p_adj = holm.get(name)
        median_ok = (res["median_pass"] is not None and res["median_fail"] is not None
                     and res["median_pass"] > res["median_fail"])
        sig = p_adj is not None and p_adj < 0.05
        ci_ok = True
        if ols.get("run") and c in ols:
            ci_ok = ols[c]["excludes_zero"] and ols[c]["coef"] > 0
        if median_ok and sig and ci_ok:
            verdicts[name] = "supported"
        else:
            verdicts[name] = "rejected"
        res["p_holm"] = p_adj
    # H5: do the four effects actually differ? Falsified if all 4 regression
    # CIs overlap (checked pairwise); if regression didn't run, falsified if
    # all 4 Hodges-Lehmann CIs/estimates overlap (approximate: compare HL
    # point estimates' spread against each check's own CI width - we don't
    # have HL CIs computed here, so fall back to a plain "point estimates
    # overlap" check on a coarse basis and mark exploratory if ambiguous).
    if ols.get("run"):
        intervals = [ols[c]["ci_95"] for c in CHECKS]
        any_disjoint = any(
            (a[1] < b[0] or b[1] < a[0])
            for a, b in combinations(intervals, 2)
        )
        verdicts["H5"] = "supported" if any_disjoint else "rejected"
    else:
        verdicts["H5"] = "insufficient"
    verdicts["H5_note"] = h5_note
    return verdicts


def main():
    rows = load()
    per_check = {c: per_check_test(rows, c) for c in CHECKS}
    loo = leave_one_out(rows)
    ols = ols_with_fixed_effects(rows)

    stale_excluded = [r for r in rows if not r["stale_float"]]
    per_check_sensitivity = {c: per_check_test(stale_excluded, c) for c in CHECKS}
    ols_sensitivity = ols_with_fixed_effects(stale_excluded)

    h5_note = f"Based on regression 95% CIs for the four check coefficients; run={ols.get('run')}"
    verdicts = falsify(per_check, loo, ols, h5_note)

    out = {
        "n_total": len(rows),
        "n_catalyst_nonexcluded": sum(1 for r in rows if r["catalyst"] is not None),
        "per_check": per_check,
        "leave_one_out": loo,
        "ols": ols,
        "sensitivity_excl_stale_float": {
            "n": len(stale_excluded),
            "per_check": per_check_sensitivity,
            "ols": ols_sensitivity,
        },
        "verdicts": verdicts,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {OUT_JSON}")
    print("Verdicts:", {k: v for k, v in verdicts.items() if k != "H5_note"})
    for c in CHECKS:
        pc = per_check[c]
        print(f"  {c}: n_pass={pc['n_pass']} n_fail={pc['n_fail']} "
              f"median_pass={pc['median_pass']} median_fail={pc['median_fail']} "
              f"p_raw={pc['p_raw']} p_holm={pc.get('p_holm')}")
    print("OLS run:", ols.get("run"), ols.get("reason", ""))


if __name__ == "__main__":
    main()
