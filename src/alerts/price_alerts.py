import pandas as pd

from alerts.base_alert import BaseAlert


class PriceAlert(BaseAlert):
    """Alerts when a ticker has dropped more than the threshold in any time window."""

    # Window -> maximum tolerated variation (%). Below it, the alert triggers.
    THRESHOLDS = {
        "var_1m": -5.0,
        "var_3m": -10.0,
        "var_6m": -15.0,
        "var_9m": -20.0,
    }

    # Trading days used to compute each window's variation.
    PERIODS = {"var_1m": 30, "var_3m": 90, "var_6m": 180, "var_9m": 270}

    def __init__(self, tickers: list[str], data_provider):
        super().__init__(tickers, data_provider)
        self.prices = self.data_provider.get_prices(tickers, period="1y", interval="1d")

    @classmethod
    def get_variations(cls, df: pd.DataFrame, var: str = "close") -> pd.DataFrame:
        """Last available row per ticker, with the variation of each window."""
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])

        for ticker in df["ticker"].unique():
            mask = df["ticker"] == ticker
            ticker_data = df[mask].sort_values("date")

            for column, periods in cls.PERIODS.items():
                df.loc[mask, column] = ticker_data[var].pct_change(periods=periods) * 100

        return df[df.groupby("ticker").cumcount(ascending=False) == 0]

    def apply_rules(self) -> pd.DataFrame:
        variations = self.get_variations(self.prices)

        triggered = False
        for column, threshold in self.THRESHOLDS.items():
            triggered = triggered | (variations[column] < threshold)

        columns = ["ticker", "date", "close", *self.THRESHOLDS]
        return variations.loc[triggered, columns]
