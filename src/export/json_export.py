"""Writes a Snapshot as the JSON files the websites consume.

The contract with the frontend is the shape of these files, not the Python
code: every file is ``{"generated_at": <ISO>, "rows": [...]}`` so metadata can
be added later without breaking any consumer.

Four files are written:
  - ``screener.json``:        the tickers that passed the fundamental filters
  - ``analyst_alerts.json``:  one row per analyst-divergence alert
  - ``price_alerts.json``:    one row per price-drop alert
  - ``companies.json``:       one row per ALERTED COMPANY, merging both tables

``companies.json`` exists because the two alert tables describe the same
companies through different numbers: the analyst rule knows the gap to the
price target, the price rule knows the variation over 1/3/6/9 months, and a
ticker firing only one of them has no value for the other. The web wants a
single card per company showing whatever is known about it, so the join is
done here, once, rather than in the browser.
"""

import json
from pathlib import Path

import pandas as pd

from pipeline import Snapshot

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
WEB_DATA_DIR = REPO_ROOT / "web" / "public" / "data"

# Columns taken from the hand-curated catalogue and attached to every row the
# web receives. ``description`` is Yahoo's own business summary: it exists for
# every ticker, so the UI always has something to show even when the LLM
# commentary is missing.
CATALOG_COLS = ["ticker", "short_name", "sector", "description"]

# The numbers each alert table contributes to a company card.
ANALYST_COLS = ["current", "median", "pct_price_diff"]
PRICE_COLS = ["var_1m", "var_3m", "var_6m", "var_9m"]

# Written by enrichment/, on whichever table happened to be enriched first.
COMMENTARY_COLS = ["business", "explanation"]


def _records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> JSON-safe rows (NaN becomes null, dates become ISO strings)."""
    if df.empty:
        return []
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _write(path: Path, generated_at: str, rows: list[dict]) -> None:
    payload = {"generated_at": generated_at, "rows": rows}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {path.name} ({len(rows)} rows)")


def _catalog() -> pd.DataFrame:
    """The hand-curated ticker data the alerts do not carry themselves."""
    return pd.read_csv(DATA_DIR / "tickers.csv")[CATALOG_COLS]


def _with_catalog(df: pd.DataFrame, catalog: pd.DataFrame) -> pd.DataFrame:
    """Adds sector and description to an alert table.

    ``short_name`` already comes from the alerts, so it is dropped from the
    catalogue side to avoid ending up with two columns holding the same name.
    """
    if df.empty:
        return df
    extra = catalog.drop(columns=["short_name"])
    return df.merge(extra, on="ticker", how="left")


def _subset(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """One row per ticker, keeping only ``cols`` that this table actually has.

    An alert table may legitimately lack a column -- ``business`` is absent
    when the run was made with ``commentary=False`` -- so the columns are
    filtered by what is there instead of being assumed.
    """
    if df.empty:
        return pd.DataFrame(columns=["ticker", *cols])
    present = [c for c in cols if c in df.columns]
    return df[["ticker", *present]].drop_duplicates(subset="ticker")


def _company_rows(snapshot: Snapshot, catalog: pd.DataFrame) -> list[dict]:
    """One row per alerted company, merging both alert tables.

    An outer join keeps companies that fired a single rule; the columns the
    other rule would have filled stay null, and the web greys them out.
    """
    analyst = _subset(snapshot.analyst_alerts, ANALYST_COLS + COMMENTARY_COLS)
    price = _subset(snapshot.price_alerts, PRICE_COLS + COMMENTARY_COLS)

    # Both sides may carry the commentary columns. Pandas keeps both and
    # suffixes the right-hand one, so they are coalesced below.
    merged = analyst.merge(price, on="ticker", how="outer", suffixes=("", "_dup"))
    for col in COMMENTARY_COLS:
        duplicate = f"{col}_dup"
        if duplicate in merged.columns:
            if col in merged.columns:
                merged[col] = merged[col].fillna(merged[duplicate])
            else:
                merged[col] = merged[duplicate]
            merged = merged.drop(columns=[duplicate])

    if merged.empty:
        return []

    merged = catalog.merge(merged, on="ticker", how="right")
    # Alphabetical so the cards do not jump around between runs.
    return _records(merged.sort_values("ticker"))


def _screened_rows(tickers: list[str], catalog: pd.DataFrame) -> list[dict]:
    """Screened tickers with their display name and sector."""
    screened = pd.DataFrame({"ticker": tickers})
    return _records(screened.merge(catalog.drop(columns=["description"]), on="ticker", how="left"))


def export_json(snapshot: Snapshot, out_dir: Path = WEB_DATA_DIR) -> None:
    """Writes one JSON file per view into ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_at = snapshot.generated_at.isoformat()
    catalog = _catalog()

    _write(out_dir / "screener.json", generated_at, _screened_rows(snapshot.screened, catalog))
    _write(
        out_dir / "analyst_alerts.json",
        generated_at,
        _records(_with_catalog(snapshot.analyst_alerts, catalog)),
    )
    _write(
        out_dir / "price_alerts.json",
        generated_at,
        _records(_with_catalog(snapshot.price_alerts, catalog)),
    )
    _write(out_dir / "companies.json", generated_at, _company_rows(snapshot, catalog))
