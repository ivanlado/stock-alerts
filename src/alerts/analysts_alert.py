import time
import random
import logging
from typing import Any, List, Dict
import pandas as pd
from ..providers.data_provider_impl import DataProviderImpl
import yfinance as yf
from .base_alert import BaseAlert

# Silenciar el logger de yfinance para que no imprima los errores HTTP;
# nosotros gestionamos e informamos los errores por ticker.
logging.getLogger("yfinance").setLevel(logging.CRITICAL)


class PriceAlert(BaseAlert):

    def __init__(self, tickers: List[str], data_provider: DataProviderImpl = None):
        super().__init__(tickers, data_provider)
        self.data = data_provider.get_analyst_targets(tickers)


    def apply_rules(self) -> List[Dict]:
        data = self.data
        data["price_diff"] = data["current"] - data["median"]
        data["pct_price_diff"] = data["price_diff"] / data["median"] * 100
        # List of tickers
        alerts = data.loc[data["pct_price_diff"] < -10]  # Example rule: alert if pct diff is less than -10%
        return alerts
    
    def alert_message(self, alerts: pd.DataFrame) -> str:
        msg = ""
        alerts = alerts.merge(self.tickers_info, on="ticker", how="left")
        for index, row in alerts.iterrows():
            aux = f"{row['ticker']}: Current={row['current']} | Median={row['median']} | Diff={row['price_diff']:.2f} | Pct Diff={row['price_diff']/row['median']*100:.1f}%\n"
            msg += aux
        return msg

    def run(self) -> List[Dict]:
        alerts = self.apply_rules()
        msg = self.alert_message(alerts)
        return msg