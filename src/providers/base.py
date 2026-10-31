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
    def get_funds(self) -> list[str]:
        """Index funds and ETFs: watched for price drops only, never screened."""
        raise NotImplementedError

    @abstractmethod
    def get_fund_details(self, funds: list[str]) -> dict[str, dict]:
        """What each fund holds: ``{ticker: {"expense_ratio", "top_holdings",
        "sectors", and optionally "countries", "countries_as_of"}}``. A fund
        the source knows nothing about is left out."""
        raise NotImplementedError

    @abstractmethod
    def get_analyst_targets(self, tickers: list[str]) -> pd.DataFrame:
        """Analysts' mean price target for each ticker."""
        raise NotImplementedError
