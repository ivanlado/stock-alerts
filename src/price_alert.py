import time
import random
import logging
from typing import Any, List, Dict
import pandas as pd
import yfinance as yf
from base_alert import BaseAlert

# Silenciar el logger de yfinance para que no imprima los errores HTTP;
# nosotros gestionamos e informamos los errores por ticker.
logging.getLogger("yfinance").setLevel(logging.CRITICAL)


class PriceAlert(BaseAlert):

    def __init__(self, tickers: List[str]):
        super().__init__(tickers)


    def get_data(self) -> pd.DataFrame:
        """
        Obtiene ratings de analistas
        """
        rows = []
        for t in self.tickers:
            # random sleep to avoid hitting API limits
            time.sleep(random.uniform(0.4, 1.7))
            try:
                pt = yf.Ticker(t).analyst_price_targets
            except Exception as e:
                print(f"Error al obtener datos de {t}: {e}")
                continue
            if pt is None:
                print(f"Sin datos de price targets para {t}")
                continue
            rows.append({
                "Ticker": t,
                "current": pt.get("current", None),
                "low": pt.get("low", None),
                "mean": pt.get("mean", None),
                "high": pt.get("high", None),
                "median": pt.get("median", None),
            })

        df = pd.DataFrame(rows)

        return df

    def apply_rules(self, data: pd.DataFrame) -> List[Dict]:
        data["price_diff"] = data["current"] - data["median"]
        q10 = data["price_diff"].quantile(0.10)
        # List of tickers
        alerts = data.loc[data["price_diff"] < q10]
        return alerts
    
    def alert_message(self, alerts: pd.DataFrame) -> str:
        msg = ""
        alerts = alerts.merge(self.tickers_info, on="Ticker", how="left")
        for index, row in alerts.iterrows():
            aux = f"{row['Ticker']}: Current={row['current']} | Median={row['median']} | Diff={row['price_diff']}\n"
            msg += aux
        return msg

    def run(self) -> List[Dict]:
        data = self.get_data()
        alerts = self.apply_rules(data)
        msg = self.alert_message(alerts)
        return msg