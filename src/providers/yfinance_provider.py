import random
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

from providers.base import DataProvider

# Repo root / data / ..., resolved relative to this file.
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
FUNDAMENTALS_CSV = DATA_DIR / "fundamentals.csv"
# The quarterly statements, cached apart from the annual ones: they have their
# own column (``period``, "2026Q2") and, unlike the annual figures, they are
# only fetched for the handful of tickers that reach the alert stage.
QUARTERLY_CSV = DATA_DIR / "fundamentals_quarterly.csv"

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

# The same three statements, yearly and quarterly. yfinance exposes the
# quarterly ones under a parallel set of attributes with identical row names,
# so one scraper serves both: only the attribute prefix changes.
_STATEMENTS = ("financials", "balance_sheet", "cashflow")


def _fetch_statements(stock: "yf.Ticker", quarterly: bool) -> dict[str, pd.DataFrame]:
    """The three statements of one ticker, keyed by their plain name.

    The keys are always ``financials`` / ``balance_sheet`` / ``cashflow``, even
    for the quarterly variant, so ``_RATIO_METRICS`` does not need to know
    which granularity it is working on.
    """
    statements: dict[str, pd.DataFrame] = {}
    for name in _STATEMENTS:
        attr = f"quarterly_{name}" if quarterly else name
        # Random sleep so we do not hit the API rate limits.
        time.sleep(random.uniform(0.4, 1.7))
        try:
            statements[name] = getattr(stock, attr)
        except Exception as e:
            print(f"Error fetching {attr}: {e}")
    return statements


def _period_label(column: object, quarterly: bool) -> int | str:
    """The value of the period column: the year, or "2026Q2" for a quarter."""
    stamp = pd.Timestamp(column)
    return f"{stamp.year}Q{stamp.quarter}" if quarterly else stamp.year


def _statement_rows(
    statements: dict[str, pd.DataFrame], ticker: str, quarterly: bool
) -> list[dict]:
    """Long-form rows (ticker, period, metric, value) for one ticker.

    Two kinds of metric end up in the same shape: the ones yfinance reports as
    a row of a statement, and the ratios computed from two rows of the same
    statement for each period.
    """
    rows: list[dict] = []
    column = "period" if quarterly else "year"

    for statement in statements.values():
        if statement is None or statement.empty:
            continue
        for period, values in statement.items():
            for metric, value in values.items():
                if metric not in FUNDAMENTAL_METRICS:
                    continue
                rows.append({
                    "ticker": ticker,
                    column: _period_label(period, quarterly),
                    "metric": metric,
                    "value": value,
                })

    for metric, name, num_row, den_row in _RATIO_METRICS:
        statement = statements.get(name)
        if statement is None or statement.empty:
            continue
        if num_row not in statement.index or den_row not in statement.index:
            continue
        for period in statement.columns:
            numerator = statement.loc[num_row, period]
            denominator = statement.loc[den_row, period]
            if pd.isna(numerator) or pd.isna(denominator) or denominator == 0:
                continue
            rows.append({
                "ticker": ticker,
                column: _period_label(period, quarterly),
                "metric": metric,
                "value": numerator / denominator,
            })

    return rows


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
        """Annual figures for every ticker, cached whole in a single CSV.

        The screener needs them for the entire universe, so the file is either
        there (and used as-is) or built in one go.
        """
        if FUNDAMENTALS_CSV.exists():
            return pd.read_csv(FUNDAMENTALS_CSV)

        rows = []
        for t in tickers:
            rows.extend(_statement_rows(_fetch_statements(yf.Ticker(t), False), t, False))

        df = pd.DataFrame(rows, columns=["ticker", "year", "metric", "value"])
        df.to_csv(FUNDAMENTALS_CSV, index=False)
        return df

    def get_quarterly_fundamentals(self, tickers: list[str]) -> pd.DataFrame:
        """The same metrics, quarter by quarter, cached PER TICKER.

        Unlike the annual ones, nothing filters on these: they exist so the web
        can show a company's recent trend, so they are only ever fetched for
        the few tickers that reach a company card. The cache therefore grows
        ticker by ticker, and each run only pays for the ones it has not seen
        before.
        """
        columns = ["ticker", "period", "metric", "value"]
        cached = pd.read_csv(QUARTERLY_CSV) if QUARTERLY_CSV.exists() else pd.DataFrame(columns=columns)

        missing = [t for t in tickers if t not in set(cached["ticker"])]
        if missing:
            print(f"Fetching quarterly fundamentals for {len(missing)} ticker(s)")
            rows = []
            for t in missing:
                rows.extend(_statement_rows(_fetch_statements(yf.Ticker(t), True), t, True))
            if rows:
                cached = pd.concat([cached, pd.DataFrame(rows, columns=columns)], ignore_index=True)
                QUARTERLY_CSV.parent.mkdir(parents=True, exist_ok=True)
                cached.to_csv(QUARTERLY_CSV, index=False)

        return cached[cached["ticker"].isin(tickers)]

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

