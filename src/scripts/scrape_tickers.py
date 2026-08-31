import json
import logging
from pathlib import Path

import pandas as pd
import yfinance as yf

from scripts.tickers import get_tickers

# Silenciar el logger de yfinance para que no imprima los errores HTTP;
# nosotros gestionamos e informamos los errores por ticker.
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
            print(f"Error al obtener info de {ticker}: {e}")
            errors.append(ticker)
            continue
        if not info:
            print(f"Sin info para {ticker}")
            errors.append(ticker)
            continue
        rows.append({
            "ticker": ticker,
            "short_name": info.get("shortName", "N/A"),
            "long_name": info.get("longName", "N/A"),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "description": info.get("longBusinessSummary", "N/A"),
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


if __name__ == "__main__":
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

    print("\n--- Resumen de errores por índice ---")
    total_err = total_all = 0
    for index, (n_err, total) in error_summary.items():
        pct = (n_err / total * 100) if total else 0.0
        print(f"{index}: {n_err}/{total} errores ({pct:.1f}%)")
        total_err += n_err
        total_all += total
    pct_all = (total_err / total_all * 100) if total_all else 0.0
    print(f"TOTAL: {total_err}/{total_all} errores ({pct_all:.1f}%)")
