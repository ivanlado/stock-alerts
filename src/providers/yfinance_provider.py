import random
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

from providers.base import DataProvider

# Repo root / data / fundamentals.csv, resolved relative to this file.
FUNDAMENTALS_CSV = Path(__file__).resolve().parents[2] / "data" / "fundamentals.csv"

# Metrics the DataFrame returned by get_fundamentals() is filtered down to.
FUNDAMENTAL_METRICS = (
    "Total Revenue",       # total revenue for the period
    "Cost Of Revenue",     # direct cost of producing/selling what was billed (COGS)
    "EBITDA",              # earnings before interest, taxes, depreciation and amortization
    "Free Cash Flow",      # free cash: operating cash flow minus capex
    "currentRatio",        # current assets / current liabilities (short-term liquidity)
    "debtToEquity",        # total debt / shareholders' equity (leverage level)
    "operatingMargins",    # operating margin = operating income / revenue
)

# Ratios in FUNDAMENTAL_METRICS that are not a row of yfinance's statements, but
# are computed from two other rows of the same statement, year by year.
# (metric, statement, numerator row, denominator row)
_RATIO_METRICS = (
    ("currentRatio", "balance_sheet", "Current Assets", "Current Liabilities"),
    ("debtToEquity", "balance_sheet", "Total Debt", "Stockholders Equity"),
    ("operatingMargins", "financials", "Operating Income", "Total Revenue"),
)


class YFinanceProvider(DataProvider):
    """Adapter towards yfinance."""

    def get_analyst_targets(self, tickers: list[str]) -> pd.DataFrame:
        rows = []
        for t in tickers:
            # Random sleep so we do not hit the API rate limits.
            time.sleep(random.uniform(0.4, 1.7))
            try:
                pt = yf.Ticker(t).analyst_price_targets
            except Exception as e:
                print(f"Error fetching data for {t}: {e}")
                continue
            if pt is None:
                print(f"No price target data for {t}")
                continue
            rows.append({
                "ticker": t,
                "current": pt.get("current", None),
                "low": pt.get("low", None),
                "mean": pt.get("mean", None),
                "high": pt.get("high", None),
                "median": pt.get("median", None),
            })

        return pd.DataFrame(rows)
    
    def get_tickers(self) -> list[str]:
        raise NotImplementedError("YFinanceProvider does not implement get_tickers()")
    
    
    def get_fundamentals(self, tickers: list[str]) -> pd.DataFrame:
        if FUNDAMENTALS_CSV.exists():
            return pd.read_csv(FUNDAMENTALS_CSV)

        rows = []
        for t in tickers:
            stock = yf.Ticker(t)
            statements = {}
            for attr in ("financials", "balance_sheet", "cashflow"):
                # Random sleep so we do not hit the API rate limits.
                time.sleep(random.uniform(0.4, 1.7))
                try:
                    statements[attr] = getattr(stock, attr)
                except Exception as e:
                    print(f"Error fetching {attr} for {t}: {e}")

            for statement in statements.values():
                if statement is None or statement.empty:
                    continue
                for year, col in statement.items():
                    for metric, value in col.items():
                        if metric not in FUNDAMENTAL_METRICS:
                            continue
                        rows.append({
                            "ticker": t,
                            "year": year.year,
                            "metric": metric,
                            "value": value,
                        })

            for metric, attr, num_row, den_row in _RATIO_METRICS:
                statement = statements.get(attr)
                if statement is None or statement.empty:
                    continue
                if num_row not in statement.index or den_row not in statement.index:
                    continue
                for year in statement.columns:
                    numerator = statement.loc[num_row, year]
                    denominator = statement.loc[den_row, year]
                    if pd.isna(numerator) or pd.isna(denominator) or denominator == 0:
                        continue
                    rows.append({
                        "ticker": t,
                        "year": year.year,
                        "metric": metric,
                        "value": numerator / denominator,
                    })

        df = pd.DataFrame(rows, columns=["ticker", "year", "metric", "value"])
        df.to_csv(FUNDAMENTALS_CSV, index=False)
        return df
    
    def get_prices(self, tickers: list[str], period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        # Download the data
        data = yf.download(tickers, period=period, interval=interval, auto_adjust=False)
        if data.empty:
            return pd.DataFrame(columns=["ticker", "date", "open", "high", "low", "close", "volume"])
        # Reshape the data so that grain is (date, ticker) and columns are open, high, low, close, volume
        data = data.stack(level=1).rename_axis(["date", "ticker"]).reset_index()
        # Remove rows without register
        data = data.dropna(subset=["Open"])
        return data[["ticker", "date", "Open", "High", "Low", "Close", "Volume"]].rename(
            columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
        )

