import pandas as pd

from providers.base import DataProvider
from providers.yfinance_provider import YFinanceProvider
from pathlib import Path
import json



# Resolve relative to the repo root (src/providers/data_provider_impl.py -> repo root)
# so it works regardless of the process's working directory.
TICKERS_DIR = Path(__file__).resolve().parents[2] / "data" / "tickers"
# Kept OUTSIDE ``TICKERS_DIR`` on purpose: a fund has no statements, so mixed
# into the stock universe the screener would discard every one of them.
FUNDS_PATH = Path(__file__).resolve().parents[2] / "data" / "funds.json"
# Written by hand with ``scripts/fund_countries.py``; optional.
FUND_COUNTRIES_PATH = Path(__file__).resolve().parents[2] / "data" / "fund_countries.json"


class DataProviderImpl(DataProvider):

    def __init__(self) -> None:
        self._yf = YFinanceProvider()

    def get_tickers(self) -> list[str]:
        tickers = []
        for path in sorted(TICKERS_DIR.glob("*.json")):
            with open(path) as f:
                tickers.extend(json.load(f))
        return list(dict.fromkeys(tickers))

    def get_funds(self) -> list[str]:
        with open(FUNDS_PATH) as f:
            return list(dict.fromkeys(json.load(f)))

    def get_fund_details(self, funds: list[str]) -> dict[str, dict]:
        """yfinance's holdings and sectors, plus the country split from the
        local file, which yfinance does not carry. ``countries_as_of`` is the
        day that file was fetched: it is refreshed by hand, so the web shows
        how old it is."""
        details = self._yf.get_fund_details(funds)
        if not FUND_COUNTRIES_PATH.exists():
            return details
        with open(FUND_COUNTRIES_PATH, encoding="utf-8") as f:
            stored = json.load(f)
        for ticker, countries in stored.get("funds", {}).items():
            if ticker in details:
                details[ticker]["countries"] = countries
                details[ticker]["countries_as_of"] = stored.get("as_of")
        return details

    def get_analyst_targets(self, tickers: list[str]) -> pd.DataFrame:
        return self._yf.get_analyst_targets(tickers)
    
    def get_fundamentals(self, tickers: list[str]) -> pd.DataFrame:
        return self._yf.get_fundamentals(tickers)

    def get_quarterly_fundamentals(self, tickers: list[str]) -> pd.DataFrame:
        return self._yf.get_quarterly_fundamentals(tickers)
    
    def get_valuation_inputs(self, tickers: list[str]) -> pd.DataFrame:
        return self._yf.get_valuation_inputs(tickers)

    def get_prices(self, tickers: list[str], period: str = "7d", interval: str = "1h") -> pd.DataFrame:
        return self._yf.get_prices(tickers, period, interval)
