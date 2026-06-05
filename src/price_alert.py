from typing import Any, List, Dict
import pandas as pd
import yfinance as yf
from base_alert import BaseAlert


class PriceAlert(BaseAlert):

    def __init__(self, tickers: List[str]):
        super().__init__(tickers)
        
        
    def get_data(self) -> pd.DataFrame:
        """
        Obtiene ratings de analistas
        """
        # df_prices = yf.download(
        #     tickers=self.tickers,  # lista de tickers
        #     period="1d",
        #     interval="1h",
        #     group_by="ticker"
        # )

        # df_prices = df_prices.stack(level=0).reset_index()
        # index_last = df_prices.groupby("Ticker")["Datetime"].idxmax()
        # df_prices = df_prices.loc[index_last].reset_index(drop=True) 
        # df_prices = df_prices.loc[:, ["Ticker", "Close"]].rename(columns={"Close":"Price"})
        
        
        rows = []
        for t in self.tickers:
            pt = yf.Ticker(t).analyst_price_targets
            rows.append({
                "Ticker": t,
                "current": pt.get("current", None),
                "low": pt.get("low", None),
                "mean": pt.get("mean", None),
                "high": pt.get("high", None),
                "median": pt.get("median", None),
            })

        df = pd.DataFrame(rows)
        # df = df.merge(df_prices, on="Ticker", how="left")

        return df

    def apply_rules(self, data: pd.DataFrame) -> List[Dict]:
        data["alert"] = data["median"] > data["current"] * 1.10 
        # List of tickers
        alerts = data.loc[data["alert"], "Ticker"].tolist()
        return alerts
    
    def run(self) -> List[Dict]:
        data = self.get_data()
        alerts = self.apply_rules(data)
        return alerts