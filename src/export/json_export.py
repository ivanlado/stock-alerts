"""Writes a Snapshot as the JSON files the websites consume.

The contract with the frontend is the shape of these files, not the Python
code: every file is ``{"generated_at": <ISO>, "rows": [...]}`` so metadata can
be added later without breaking any consumer.

These files are written:
  - ``screener.json``:        the tickers that passed the fundamental filters
  - ``analyst_alerts.json``:  one row per analyst-divergence alert
  - ``price_alerts.json``:    one row per price-drop alert
  - ``companies.json``:       one row per stock of the UNIVERSE and per FUND,
                              merging both tables
  - ``prices/<ticker>.json``: the price history of one stock or fund, a file
                              each so the browser downloads only the chart it
                              opens instead of hundreds of series up front

``companies.json`` exists because the two alert tables describe the same
companies through different numbers: the analyst rule knows the gap to the
price target, the price rule knows the variation over a day, a week,
1/3/6/9 months and a year. The web wants a single card per company showing
whatever is known about it, so the join is done here, once, rather than in the
browser.

EVERY STOCK of the universe is on that list, screened or not, because Search
filters all of them; ``screened`` says which ones passed the fundamental
filters. ``analyst_alert`` / ``price_alert`` say which rule fired, if any --
only a screened stock or a fund can fire -- and the rows that did fire come
first. The alert pages show only those.

Their numbers come from the UNFILTERED tables (``analyst_all``, ``price_all``),
so a card always shows both rules: firing only the price rule never meant the
gap to the analyst target was unknown, only that it was not wide enough to
alert on.
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
PRICE_COLS = ["var_1d", "var_1w", "var_1m", "var_3m", "var_6m", "var_9m", "var_1y"]

# Written by enrichment/commentary.py onto the rows that alerted. Only those:
# a rule that did not fire has nothing to explain.
COMMENTARY_COLS = ["explanation"]

# How much price history the web receives, and how finely. Every trading day of
# the last year, one point a week before that: the chart offers a 3-month view,
# which needs daily points, and a 5-year one, where 1300 daily points would
# paint the same line as 260 weekly ones at five times the download.
DAILY_WINDOW_DAYS = 365

# Fundamentals the web receives, mapped from the metric name used in
# ``data/fundamentals.csv`` to the key the frontend reads. The first three are
# the ratios the screener itself filters on, which is why they are the ones
# the cards lead with.
FUNDAMENTAL_FIELDS = {
    "operatingMargins": "operating_margin",
    "debtToEquity": "debt_to_equity",
    "currentRatio": "current_ratio",
    # Computed, not fetched: these two need a price, so they come from
    # ``valuation.py`` and exist for the annual table only (a PER on a single
    # quarter's earnings would read four times too high).
    "priceEarnings": "price_earnings",
    "priceToSales": "price_to_sales",
    "Total Revenue": "total_revenue",
    "Cost Of Revenue": "cost_of_revenue",
    "EBITDA": "ebitda",
    "Free Cash Flow": "free_cash_flow",
}

# Stored as a fraction (0.18) but shown as a percentage (18.0%).
PERCENT_FIELDS = {"operating_margin"}


def _records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> JSON-safe rows (NaN becomes null, dates become ISO strings)."""
    if df.empty:
        return []
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _write(path: Path, generated_at: str, rows: list[dict], compact: bool = False) -> None:
    """``compact`` drops the indentation: for the price files, which are
    almost all numbers, it would add a third to their size for nobody to read.
    """
    payload = {"generated_at": generated_at, "rows": rows}
    text = (
        json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        if compact
        else json.dumps(payload, indent=2, ensure_ascii=False)
    )
    path.write_text(text, encoding="utf-8")
    if not compact:
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

    An alert table may legitimately lack a column -- ``explanation`` is absent
    when the run was made with ``commentary=False`` -- so the columns are
    filtered by what is there instead of being assumed.
    """
    if df.empty:
        return pd.DataFrame(columns=["ticker", *cols])
    present = [c for c in cols if c in df.columns]
    return df[["ticker", *present]].drop_duplicates(subset="ticker")


def _fundamentals_by_ticker(fundamentals: pd.DataFrame, period_col: str) -> dict[str, dict]:
    """Long-form (ticker, period, metric, value) -> one entry per ticker.

    ``period_col`` is the column holding the period: ``year`` (2025) for the
    annual table, ``period`` ("2025Q3") for the quarterly one. Both end up in
    the same shape, so the web renders them with the same component.

    Each entry is ``{"latest": {...}, "history": [...]}``: the most recent
    period for the card, and every period for the detail panel. Every one
    carries every key, filled with None when the source has no value, so the
    web can lay them out as a table without checking which columns exist.

    The periods sort as strings ("2025Q3" < "2025Q4" < "2026Q1"), which is the
    chronological order for both formats.
    """
    if fundamentals.empty or period_col not in fundamentals.columns:
        return {}

    wanted = fundamentals[fundamentals["metric"].isin(FUNDAMENTAL_FIELDS)]
    by_ticker: dict[str, dict] = {}

    for ticker, rows in wanted.groupby("ticker"):
        periods = []
        for period, period_rows in rows.groupby(period_col):
            entry: dict = {"period": str(period)}
            entry.update({name: None for name in FUNDAMENTAL_FIELDS.values()})
            for metric, value in zip(period_rows["metric"], period_rows["value"]):
                if pd.isna(value):
                    continue
                name = FUNDAMENTAL_FIELDS[metric]
                entry[name] = float(value) * 100 if name in PERCENT_FIELDS else float(value)
            # yfinance reports the odd period with no figure in it at all --
            # a quarter it knows the date of and nothing else. A column of
            # dashes is worse than no column.
            if any(entry[name] is not None for name in FUNDAMENTAL_FIELDS.values()):
                periods.append(entry)

        if not periods:
            continue

        periods.sort(key=lambda entry: entry["period"])
        by_ticker[str(ticker)] = {"latest": periods[-1], "history": periods}

    return by_ticker


def _company_rows(snapshot: Snapshot, catalog: pd.DataFrame) -> list[dict]:
    """One row per stock of the universe and per fund, merging both rule tables.

    ``screened`` marks the stocks that passed the fundamental filters.
    ``asset_type`` tells stocks and funds apart: a fund ("fund") has no statements, no
    analyst target and no profile, so the web hides those blocks instead of
    painting a card full of dashes.
    """
    tickers = (snapshot.universe or snapshot.screened) + snapshot.funds
    if not tickers:
        return []

    analyst = _subset(snapshot.analyst_all, ANALYST_COLS)
    price = _subset(snapshot.price_all, PRICE_COLS)

    merged = analyst.merge(price, on="ticker", how="outer")
    # An outer join only knows the tickers its two sides carry. Starting from
    # the screened list instead means a company whose price target could not be
    # downloaded still gets a card, with that number missing.
    merged = pd.DataFrame({"ticker": tickers}).merge(merged, on="ticker", how="left")
    merged["asset_type"] = merged["ticker"].isin(snapshot.funds).map({True: "fund", False: "stock"})
    merged["screened"] = merged["ticker"].isin(snapshot.screened)

    merged = merged.merge(_explanations(snapshot), on="ticker", how="left")
    merged["analyst_alert"] = merged["ticker"].isin(_tickers(snapshot.analyst_alerts))
    merged["price_alert"] = merged["ticker"].isin(_tickers(snapshot.price_alerts))

    if merged.empty:
        return []

    merged = catalog.merge(merged, on="ticker", how="right")
    # What fired comes first, and alphabetically within each group, so the
    # cards do not jump around between runs.
    merged["alerted"] = merged["analyst_alert"] | merged["price_alert"]
    merged = merged.sort_values(["alerted", "ticker"], ascending=[False, True])
    rows = _records(merged.drop(columns=["alerted"]))

    # Attached after the DataFrame work because these are nested objects, not
    # flat columns, and pandas has no use for them.
    annual = _fundamentals_by_ticker(snapshot.fundamentals, "year")
    quarterly = _fundamentals_by_ticker(snapshot.fundamentals_quarterly, "period")
    valuation = _valuation_by_ticker(snapshot.valuation)
    for row in rows:
        entry = annual.get(row["ticker"])
        row["fundamentals"] = entry["latest"] if entry else None
        row["fundamentals_history"] = entry["history"] if entry else []
        row["revenue_growth"] = _revenue_growth(row["fundamentals_history"])
        quarters = quarterly.get(row["ticker"])
        row["fundamentals_quarterly"] = quarters["history"] if quarters else []
        profile = snapshot.profiles.get(row["ticker"]) or {}
        row["profile"] = profile.get("sections") or None
        # Today's PER and price/sales, which belong to no period: the card
        # leads with these, and `fundamentals_history` carries the year-by-year
        # series of the same two ratios underneath.
        today = valuation.get(row["ticker"], {})
        row["trailing_pe"] = today.get("trailing_pe")
        row["price_to_sales"] = today.get("price_to_sales")
        # What a fund holds; null for a company, and for a fund the source
        # had nothing on today.
        row["fund"] = snapshot.fund_details.get(row["ticker"])

    return rows


def _revenue_growth(history: list[dict]) -> float | None:
    """Last reported year's revenue against the year before, in percent.

    ``history`` is oldest first. None when two consecutive years with revenue
    are not there, or the earlier one is not positive (a growth rate off a
    zero or negative base is arithmetic, not information).
    """
    years = [entry for entry in history if entry.get("total_revenue") is not None]
    if len(years) < 2:
        return None
    previous, latest = years[-2]["total_revenue"], years[-1]["total_revenue"]
    if previous <= 0:
        return None
    return (latest / previous - 1) * 100


def _valuation_by_ticker(valuation: pd.DataFrame) -> dict[str, dict]:
    """``{ticker: {"trailing_pe": ..., "price_to_sales": ...}}``, NaN dropped.

    yfinance leaves both empty for a company with no earnings to divide by, so
    a missing key here is a normal state and the card greys the badge out.
    """
    if valuation.empty:
        return {}
    out: dict[str, dict] = {}
    for row in valuation.to_dict("records"):
        out[str(row["ticker"])] = {
            key: (None if pd.isna(row.get(key)) else float(row[key]))
            for key in ("trailing_pe", "price_to_sales")
        }
    return out


def _tickers(df: pd.DataFrame) -> set[str]:
    return set() if df.empty else set(df["ticker"].astype(str))


def _explanations(snapshot: Snapshot) -> pd.DataFrame:
    """One ``explanation`` per ticker, from whichever rule managed to write it.

    A ticker firing both rules has two of them; the analyst one wins, and the
    price one fills in whatever it left empty.
    """
    analyst = _subset(snapshot.analyst_alerts, COMMENTARY_COLS)
    price = _subset(snapshot.price_alerts, COMMENTARY_COLS)

    merged = analyst.merge(price, on="ticker", how="outer", suffixes=("", "_dup"))
    for col in COMMENTARY_COLS:
        duplicate = f"{col}_dup"
        if duplicate in merged.columns:
            if col in merged.columns:
                merged[col] = merged[col].fillna(merged[duplicate])
            else:
                merged[col] = merged[duplicate]
            merged = merged.drop(columns=[duplicate])
        elif col not in merged.columns:
            # The run was made with commentary=False.
            merged[col] = None

    return merged[["ticker", *COMMENTARY_COLS]]


def _price_rows(prices: pd.DataFrame) -> list[dict]:
    """One row per ticker: ``{"ticker": ..., "points": [[date, close], ...]}``.

    A pair instead of an object per point because the file is mostly this: the
    same two keys repeated thousands of times would double its size for no
    added meaning.
    """
    if prices.empty:
        return []

    df = prices[["ticker", "date", "close"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["close"]).sort_values(["ticker", "date"])

    cutoff = df["date"].max() - pd.Timedelta(days=DAILY_WINDOW_DAYS)
    recent = df[df["date"] >= cutoff]
    # One point per calendar week for the older stretch: the last close of
    # each, keeping the real trading date rather than the week's end.
    older = df[df["date"] < cutoff].copy()
    if not older.empty:
        older["week"] = older["date"].dt.to_period("W")
        weekly = older.drop_duplicates(subset=["ticker", "week"], keep="last")
        df = pd.concat([weekly.drop(columns=["week"]), recent]).sort_values(["ticker", "date"])

    rows = []
    for ticker, group in df.groupby("ticker"):
        points = [
            [date.strftime("%Y-%m-%d"), round(float(close), 4)]
            for date, close in zip(group["date"], group["close"])
        ]
        rows.append({"ticker": str(ticker), "points": points})
    return rows


def _write_prices(out_dir: Path, generated_at: str, series: list[dict]) -> None:
    """One file per ticker under ``prices/``, each with that ticker's series
    as its single row, so the file keeps the ``{generated_at, rows}`` shape
    of every other one.

    The directory is emptied first: a ticker that left the universe must not
    leave a stale chart behind. ``prices.json``, the single file this replaced,
    is removed for the same reason.
    """
    prices_dir = out_dir / "prices"
    prices_dir.mkdir(parents=True, exist_ok=True)
    for old in prices_dir.glob("*.json"):
        old.unlink()
    (out_dir / "prices.json").unlink(missing_ok=True)

    for row in series:
        _write(prices_dir / f"{row['ticker']}.json", generated_at, [row], compact=True)
    print(f"Wrote prices/ ({len(series)} files)")


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
    _write_prices(out_dir, generated_at, _price_rows(snapshot.prices))
