import pandas as pd

from alerts.base_alert import BaseAlert


class PriceAlert(BaseAlert):
    """Alerts when a ticker has dropped more than the threshold in any time window."""

    # Window -> maximum tolerated variation (%). Below it, the alert triggers.
    THRESHOLDS = {
        "var_1d": -5.0,
        "var_1w": -5.0,
        "var_1m": -5.0,
        "var_3m": -10.0,
        "var_6m": -15.0,
        "var_9m": -20.0,
        "var_1y": -15.0,
    }

    # How far back each window looks, in CALENDAR time. Counting trading rows
    # instead would make "1M" mean 30 sessions -- about six weeks -- and "9M"
    # more than a year, so the labels would lie. ``var_1d`` is the exception:
    # it is the previous session, whatever its date (see ``get_variations``).
    OFFSETS = {
        "var_1w": pd.DateOffset(weeks=1),
        "var_1m": pd.DateOffset(months=1),
        "var_3m": pd.DateOffset(months=3),
        "var_6m": pd.DateOffset(months=6),
        "var_9m": pd.DateOffset(months=9),
        "var_1y": pd.DateOffset(years=1),
    }

    # How much price history the windows need. The longest one looks a year
    # back, so a single year of daily rows would leave it at the very edge.
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
        """Last available row per ticker, with the variation of each window.

        Every window compares the LAST price against an earlier close. At 14:00
        in Spain the last row of a European ticker is today's session still in
        progress, and the last row of an American one is yesterday's close (Wall
        Street has not opened yet). Either way ``var_1d`` is that last price
        against the session before it, which is the move nobody has seen yet.

        The longer windows take the close of the last session on or before the
        same calendar date that many weeks/months back, so a weekend or a bank
        holiday falls back to the Friday before it. A ticker whose history does
        not reach that far gets NaN rather than a variation over a shorter span.
        """
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])

        rows = []
        for ticker, ticker_data in df.groupby("ticker"):
            ticker_data = ticker_data.dropna(subset=[var]).sort_values("date")
            if ticker_data.empty:
                continue
            dates = ticker_data["date"]
            closes = ticker_data[var].to_numpy()
            last = ticker_data.iloc[-1].copy()
            last_price = closes[-1]

            last["var_1d"] = (last_price / closes[-2] - 1) * 100 if len(closes) > 1 else float("nan")
            for column, offset in cls.OFFSETS.items():
                # `searchsorted(side="right") - 1` is the index of the last date
                # on or before the target, found by binary search.
                index = dates.searchsorted(last["date"] - offset, side="right") - 1
                last[column] = (last_price / closes[index] - 1) * 100 if index >= 0 else float("nan")
            rows.append(last)

        columns = [*df.columns, *cls.THRESHOLDS]
        return pd.DataFrame(rows, columns=columns).reset_index(drop=True)

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
