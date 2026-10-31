import json
import logging
import random
import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

from scripts.tickers import get_tickers

# Silence yfinance's logger so it does not print the HTTP errors;
# we handle and report the errors per ticker ourselves.
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
TICKERS_DIR = DATA_DIR / "tickers"
TICKERS_CSV = DATA_DIR / "tickers.csv"

INDICES = ["sp500", "ibex35"]


def _fetch_ticker_info(ticker_list: list[str]) -> tuple[pd.DataFrame, list[str]]:
    tickers = yf.Tickers(" ".join(ticker_list))
    rows = []
    errors: list[str] = []
    for ticker, obj in tickers.tickers.items():
        try:
            info = obj.info
        except Exception as e:
            print(f"Error fetching info for {ticker}: {e}")
            errors.append(ticker)
            continue
        if not info:
            print(f"No info for {ticker}")
            errors.append(ticker)
            continue
        rows.append({
            "ticker": ticker,
            "short_name": info.get("shortName", "N/A"),
            "long_name": info.get("longName", "N/A"),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "description": info.get("longBusinessSummary", "N/A"),
            "country": info.get("country"),
        })
    return pd.DataFrame(rows), errors


def _update_csv(new_df: pd.DataFrame) -> None:
    if TICKERS_CSV.exists():
        existing = pd.read_csv(TICKERS_CSV)
        existing = existing[~existing["ticker"].isin(new_df["ticker"])]
        merged = pd.concat([existing, new_df], ignore_index=True)
    else:
        merged = new_df
    merged.sort_values("ticker", inplace=True)
    merged.to_csv(TICKERS_CSV, index=False)


def backfill_country() -> None:
    """Fills the ``country`` column for the rows that lack it, touching nothing else.

    Run with ``python -m scripts.scrape_tickers --country``. It exists because
    the column was added after the catalogue was built, and a full scrape would
    rewrite every row -- including the hand-written fund rows. A fund has no
    country of its own (its holdings span many), so those stay empty.
    """
    catalog = pd.read_csv(TICKERS_CSV)
    if "country" not in catalog.columns:
        catalog["country"] = None
    pending = catalog.loc[catalog["country"].isna() & (catalog["sector"] != "Fund"), "ticker"]
    print(f"Fetching the country of {len(pending)} ticker(s)")
    for ticker in pending:
        time.sleep(random.uniform(0.1, 0.4))
        try:
            country = yf.Ticker(ticker).info.get("country")
        except Exception as e:
            print(f"Error fetching info for {ticker}: {e}")
            continue
        catalog.loc[catalog["ticker"] == ticker, "country"] = country
    catalog.to_csv(TICKERS_CSV, index=False)
    print(f"Countries known: {catalog['country'].notna().sum()} of {len(catalog)}")


if __name__ == "__main__" and "--country" in sys.argv:
    backfill_country()
elif __name__ == "__main__":
    TICKERS_DIR.mkdir(parents=True, exist_ok=True)
    all_info = []
    error_summary = {}
    for index in INDICES:
        ticker_list = get_tickers(index)
        path = TICKERS_DIR / f"{index}.json"
        with open(path, "w") as f:
            json.dump(ticker_list, f, indent=2)
        print(f"{index}: {len(ticker_list)} tickers -> {path}")

        print(f"Fetching company information for {index}...")
        info_df, errors = _fetch_ticker_info(ticker_list)
        all_info.append(info_df)
        error_summary[index] = (len(errors), len(ticker_list))

    combined = pd.concat(all_info, ignore_index=True).drop_duplicates(subset="ticker", keep="last")
    _update_csv(combined)
    print(f"Ticker info saved to {TICKERS_CSV}")

    print("\n--- Error summary per index ---")
    total_err = total_all = 0
    for index, (n_err, total) in error_summary.items():
        pct = (n_err / total * 100) if total else 0.0
        print(f"{index}: {n_err}/{total} errors ({pct:.1f}%)")
        total_err += n_err
        total_all += total
    pct_all = (total_err / total_all * 100) if total_all else 0.0
    print(f"TOTAL: {total_err}/{total_all} errors ({pct_all:.1f}%)")
