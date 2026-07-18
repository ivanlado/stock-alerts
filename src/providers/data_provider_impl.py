import pandas as pd

from providers.base import DataProvider
from providers.yfinance_provider import YFinanceProvider
from pathlib import Path
import json



TICKERS_DIR = Path("data") / "tickers"


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
