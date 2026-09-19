import logging
from typing import List

import pandas as pd

from alerts.base_alert import BaseAlert
from providers.base import DataProvider

# Silence yfinance's logger so it does not print the HTTP errors;
# we handle and report the errors per ticker ourselves.
logging.getLogger("yfinance").setLevel(logging.CRITICAL)


class AnalystAlerts(BaseAlert):
    """Alerts when the current price is well below the analysts' median target."""

    MAX_PCT_DIFF = -10.0

    def __init__(self, tickers: List[str], data_provider: DataProvider):
        super().__init__(tickers, data_provider)
        self.data = data_provider.get_analyst_targets(tickers)

    def compute(self) -> pd.DataFrame:
        """Gap to the analysts' median target for every ticker, alert or not."""
        data = self.data.copy()
        data["price_diff"] = data["current"] - data["median"]
        data["pct_price_diff"] = data["price_diff"] / data["median"] * 100
        return data

    def apply_rules(self) -> pd.DataFrame:
        data = self.compute()
        return data.loc[data["pct_price_diff"] < self.MAX_PCT_DIFF]
