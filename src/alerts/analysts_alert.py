import logging
from typing import List

import pandas as pd

from alerts.base_alert import BaseAlert
from providers.base import DataProvider

# Silenciar el logger de yfinance para que no imprima los errores HTTP;
# nosotros gestionamos e informamos los errores por ticker.
logging.getLogger("yfinance").setLevel(logging.CRITICAL)


class AnalystAlerts(BaseAlert):
    """Alerts when the current price is well below the analysts' median target."""

    MAX_PCT_DIFF = -10.0

    def __init__(self, tickers: List[str], data_provider: DataProvider):
        super().__init__(tickers, data_provider)
        self.data = data_provider.get_analyst_targets(tickers)

    def apply_rules(self) -> pd.DataFrame:
        data = self.data.copy()
        data["price_diff"] = data["current"] - data["median"]
        data["pct_price_diff"] = data["price_diff"] / data["median"] * 100
        return data.loc[data["pct_price_diff"] < self.MAX_PCT_DIFF]
