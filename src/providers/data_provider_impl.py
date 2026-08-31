import pandas as pd

from providers.base import DataProvider
from providers.yfinance_provider import YFinanceProvider
from pathlib import Path
import json



# Resolve relative to the repo root (src/providers/data_provider_impl.py -> repo root)
# so it works regardless of the process's working directory.
TICKERS_DIR = Path(__file__).resolve().parents[2] / "data" / "tickers"


class DataProviderImpl(DataProvider):

    def __init__(self) -> None:
        self._yf = YFinanceProvider()

    def get_tickers(self) -> list[str]:
        tickers = []
        for path in sorted(TICKERS_DIR.glob("*.json")):
            with open(path) as f:
                tickers.extend(json.load(f))
        return list(dict.fromkeys(tickers))

    def get_analyst_targets(self, tickers: list[str]) -> pd.DataFrame:
        return self._yf.get_analyst_targets(tickers)
    
    def get_fundamentals(self, tickers: list[str]) -> pd.DataFrame:
        return self._yf.get_fundamentals(tickers)
    
    def get_prices(self, tickers: list[str], period: str = "7d", interval: str = "1h") -> pd.DataFrame:
        return self._yf.get_prices(tickers, period, interval)
