"""Writes a Snapshot as the JSON files the websites consume.

The contract with the frontend is the shape of these files, not the Python
code: every file is ``{"generated_at": <ISO>, "rows": [...]}`` so metadata can
be added later without breaking any consumer.
"""

import json
from pathlib import Path

import pandas as pd

from pipeline import Snapshot

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
WEB_DATA_DIR = REPO_ROOT / "web" / "public" / "data"


def _records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> JSON-safe rows (NaN becomes null, dates become ISO strings)."""
    if df.empty:
        return []
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _write(path: Path, generated_at: str, rows: list[dict]) -> None:
    payload = {"generated_at": generated_at, "rows": rows}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {path.name} ({len(rows)} rows)")


def _screened_rows(tickers: list[str]) -> list[dict]:
    """Screened tickers with their display name."""
    names = pd.read_csv(DATA_DIR / "tickers.csv")[["ticker", "short_name"]]
    screened = pd.DataFrame({"ticker": tickers})
    return _records(screened.merge(names, on="ticker", how="left"))


def export_json(snapshot: Snapshot, out_dir: Path = WEB_DATA_DIR) -> None:
    """Writes one JSON file per view into ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_at = snapshot.generated_at.isoformat()

    _write(out_dir / "screener.json", generated_at, _screened_rows(snapshot.screened))
    _write(out_dir / "analyst_alerts.json", generated_at, _records(snapshot.analyst_alerts))
    _write(out_dir / "price_alerts.json", generated_at, _records(snapshot.price_alerts))
