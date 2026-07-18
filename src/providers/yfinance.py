import random
import time

import pandas as pd
import yfinance as yf

from providers.base import DataProvider


class YFinanceProvider(DataProvider):
    """Adaptador hacia yfinance."""

    def get_analyst_targets(self, tickers: list[str]) -> pd.DataFrame:
        rows = []
        for t in tickers:
            # sleep aleatorio para no saturar los límites de la API
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
                "ticker": t,
                "current": pt.get("current", None),
                "low": pt.get("low", None),
                "mean": pt.get("mean", None),
                "high": pt.get("high", None),
                "median": pt.get("median", None),
            })

        return pd.DataFrame(rows)
    
    def get_tickers(self) -> list[str]:
        raise NotImplementedError("YFinanceProvider does not implement get_tickers()")
