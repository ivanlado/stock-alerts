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

    # How much price history the windows need. The longest one looks 270 rows
    # back, so a single year of daily rows leaves it with nothing to compare
    # against and ``var_9m`` comes out empty for every ticker.
    PERIOD = "5y"

    def __init__(self, tickers: list[str], data_provider, prices: pd.DataFrame | None = None):
        """``prices`` lets the caller hand over a history it has already
        downloaded -- the pipeline needs the same series for the web chart --
        instead of paying for the same request twice."""
        super().__init__(tickers, data_provider)
        self.prices = (
            prices
            if prices is not None
            else self.data_provider.get_prices(tickers, period=self.PERIOD, interval="1d")
        )

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

    def compute(self) -> pd.DataFrame:
        """Last close and the variation of every window, for every ticker."""
        columns = ["ticker", "date", "close", *self.THRESHOLDS]
        return self.get_variations(self.prices)[columns]

    def apply_rules(self) -> pd.DataFrame:
        variations = self.compute()

        triggered = False
        for column, threshold in self.THRESHOLDS.items():
            triggered = triggered | (variations[column] < threshold)

        return variations.loc[triggered]
