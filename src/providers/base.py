from abc import ABC, abstractmethod

import pandas as pd


class DataProvider(ABC):
    """Port (in the hexagonal architecture sense) towards the market data source.

    Every concrete adapter (yfinance, etc.) lives in its own file and implements
    this interface. When new capabilities are added (e.g. ``get_fundamentals``),
    they are declared here and every adapter must provide them.
    """
    @abstractmethod
    def get_tickers(self) -> list[str]:
        """Tickers available in the data source."""
        raise NotImplementedError

    @abstractmethod
    def get_analyst_targets(self, tickers: list[str]) -> pd.DataFrame:
        """Analysts' mean price target for each ticker."""
        raise NotImplementedError
