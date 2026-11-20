"""Build the claude.ai artifact copy of the dashboard.

Artifact pages cannot fetch raw.githubusercontent.com, so the artifact reads
state.json, ledger.jsonl, report.md and alerts.md published beside it. This
script strips the html/head/body wrapper (the artifact adds its own), points
the page at those files, and adds a "snapshot" notice with the run time.

Usage: python3 make_artifact_copy.py index.html <out_dir>/index.html <out_dir>/state.json
"""
import re, sys, json, datetime
src, out, state = sys.argv[1], sys.argv[2], sys.argv[3]
h = open(src).read()
# Artifact skeleton supplies doctype/html/head/body and the charset/viewport metas.
for pat in [r'<!doctype html>\s*', r'<html[^>]*>\s*', r'</html>\s*', r'<head>\s*', r'</head>\s*', r'<body>\s*', r'</body>\s*',
            r'<meta charset="utf-8">\s*', r'<meta name="viewport"[^>]*>\s*']:
    h, n = re.subn(pat, '', h, count=1, flags=re.I)
    assert n == 1, pat
h = h.replace('<title>Paper Trader Dashboard</title>', '<title>Paper Trader Dashboard</title>\n<meta name="claude:viewport-fit-sides" content="cover">', 1)
# Read the data files published beside the page (external fetches are blocked on artifact pages).
assert h.count('const LIVE_BASE = "https://raw.githubusercontent.com/calebkemp310/calebkemp310/paper-trading/";') == 1
h = h.replace('const LIVE_BASE = "https://raw.githubusercontent.com/calebkemp310/calebkemp310/paper-trading/";', 'const LIVE_BASE = "./";')
snap = json.load(open(state)).get("last_success") or ""
t = snap[:16].replace("T", " ") + " UTC" if snap else "unknown time"
note = ('  notices.push({ id: "snapshot-notice", tone: "info", text: "Snapshot of the paper trader from its run at ' + t +
        '. This page doesn\\u2019t update by itself: ask Claude to refresh it." });\n')
anchor = '  let nowOverride = null;\n'
assert h.count(anchor) == 1
h = h.replace(anchor, note + anchor)
open(out, 'w').write(h)
print("ok, snapshot", t, len(h), "bytes")
