"""Paper account state (state.json) and the append-only ledger (ledger.jsonl).

state.json carries a sha256 checksum of its own content. A missing checksum,
a mismatch or bad JSON raises StateError, and the runner then does nothing.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

VERSION = 1


class StateError(Exception):
    pass


def new_state(start_equity: float, now: datetime) -> dict:
    return {
        "version": VERSION,
        "armed": True,
        "started": now.isoformat(),
        "start_equity": start_equity,
        "cash": start_equity,
        "positions": {},              # product -> {qty, entry_px, entry_time, stop, weight}
        "shadow": {"cash": start_equity, "positions": {}},  # taker-fill twin book
        "peak_equity": start_equity,
        "day": now.date().isoformat(),
        "day_start_equity": start_equity,
        "entries_today": {},
        "stopped_latch": {},          # product -> True after a catastrophe stop, until signal goes flat
        "last_processed_bar": None,   # ISO date of the last daily bar acted on
        "errors": {"consecutive": 0, "recent": []},
        "frozen": False,
        "daily_loss_alerted": None,
        "last_run": None,
        "last_success": None,
    }


def _digest(body: dict) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def save(state: dict, path: Path) -> None:
    body = {k: v for k, v in state.items() if k != "checksum"}
    out = dict(body, checksum=_digest(body))
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(out, indent=1, sort_keys=True))
    tmp.replace(path)  # atomic on the same filesystem


def load(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise StateError(f"cannot read {path}: {e}") from e
    chk = raw.pop("checksum", None)
    if chk is None or chk != _digest(raw):
        raise StateError(f"{path} checksum mismatch: refusing to trade on edited or corrupt state")
    if raw.get("version") != VERSION:
        raise StateError(f"unsupported state version {raw.get('version')}")
    return raw


def append_ledger(path: Path, records: list[dict]) -> None:
    """Append only. Never rewrites earlier lines."""
    with path.open("a") as f:
        for r in records:
            f.write(json.dumps(r, sort_keys=True, default=str) + "\n")


def read_ledger(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
