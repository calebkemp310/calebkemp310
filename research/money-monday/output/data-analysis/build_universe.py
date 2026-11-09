#!/usr/bin/env python3
"""Task 2: build the Monday gapper universe from cached Benzinga movers article HTML.
Run with: python3 -I build_universe.py
Reads input/data/posts.csv (date,news_id,title), fetches/caches each article's HTML,
parses "Gainers" mentions, filters gap>=10% and price<$20, de-dupes on (date,ticker).
Writes input/data/universe.csv.
"""
import csv, html, re, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # research/money-monday
POSTS_CSV = ROOT / "input/data/posts.csv"
HTML_DIR = ROOT / "input/data/posts_html"
OUT_CSV = ROOT / "input/data/universe.csv"

HTML_DIR.mkdir(parents=True, exist_ok=True)

GAIN_VERB = r"(?:rose|increased|gained|jumped|surged|climbed|up|moved upwards|moved up)"
# Match: "<Name> (EXCH: TICK) stock|shares <verb> [by] N% to $P"
PATTERN = re.compile(
    r"\(([A-Z]{2,6}):\s*([A-Z]{1,6})\s*\)\s*(?:stock|shares)\s+(?:" + GAIN_VERB + r")\s+(?:by\s+)?([\d.]+)%\s+to\s+\$([\d.]+)",
    re.IGNORECASE,
)

def fetch(date_str, news_id):
    ymd = date_str.replace("-", "")
    path = HTML_DIR / f"{ymd}_{news_id}.html"
    if path.exists():
        return path.read_text(encoding="utf-8", errors="ignore")
    url = f"https://news-static.webullfintech.com/us/news-html/{ymd}/{news_id}.html"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = resp.read().decode("utf-8", errors="ignore")
    path.write_text(data, encoding="utf-8")
    return data

def to_text(raw_html):
    # Strip script blocks and tags, unescape entities, collapse whitespace.
    no_script = re.sub(r"<script\b[^>]*>.*?</script>", " ", raw_html, flags=re.DOTALL | re.IGNORECASE)
    no_tags = re.sub(r"<[^>]+>", " ", no_script)
    text = html.unescape(no_tags)
    return re.sub(r"\s+", " ", text)

def extract_gainers_section(text):
    # Only look at the "Gainers" part, before "Losers", to avoid misreading decliners.
    m = re.search(r"Gainers(.*?)(?:Losers|$)", text, flags=re.IGNORECASE)
    return m.group(1) if m else text

def main():
    if not POSTS_CSV.exists():
        print(f"ERROR: {POSTS_CSV} not found", file=sys.stderr)
        sys.exit(1)
    rows = list(csv.DictReader(open(POSTS_CSV, encoding="utf-8")))
    seen = {}  # (date, ticker) -> row, first match wins
    fetch_errors = []
    parse_zero = []
    for r in rows:
        date_str, news_id, title = r["date"], r["news_id"], r["title"]
        try:
            raw = fetch(date_str, news_id)
        except Exception as e:
            fetch_errors.append((date_str, news_id, str(e)))
            continue
        text = to_text(raw)
        gainers_text = extract_gainers_section(text)
        matches = PATTERN.findall(gainers_text)
        if not matches:
            parse_zero.append((date_str, news_id, title))
            continue
        for exch, ticker, pct_str, price_str in matches:
            pct = float(pct_str.rstrip("."))
            price = float(price_str.rstrip("."))
            if pct >= 10.0 and price < 20.0:
                key = (date_str, ticker)
                if key not in seen:
                    seen[key] = {
                        "date": date_str,
                        "ticker": ticker,
                        "gap_pct": pct,
                        "pm_price": price,
                        "source_post_id": news_id,
                    }
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "ticker", "gap_pct", "pm_price", "source_post_id"])
        w.writeheader()
        for key in sorted(seen):
            w.writerow(seen[key])
    print(f"Wrote {len(seen)} rows to {OUT_CSV}")
    print(f"Fetch errors: {len(fetch_errors)}")
    for e in fetch_errors[:10]:
        print("  FETCH ERR", e)
    print(f"Posts with 0 gainer matches: {len(parse_zero)}")
    for z in parse_zero[:15]:
        print("  ZERO MATCH", z)

if __name__ == "__main__":
    main()
