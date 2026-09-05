import pandas as pd

from providers.base import DataProvider


class FundamentalScreener:
    """Filters a list of tickers based on fundamental criteria.

    The criteria are passed as a ``dict`` so the constructor does not grow when
    new metrics are added. A new criterion = a key in the dict + a ``_xxx_ok``
    method + one line in ``_passes``.
    """

    # Defaults in a single place; the input dict only overrides what it wants to.
    DEFAULT_CRITERIA = {
        "max_debt_to_equity": 1.0,      # 100%, last year only
        "min_operating_margin": 0.07,   # 7%, in each of the last N years
        "operating_margin_years": 3,
    }

    def __init__(
        self,
        data_provider: DataProvider,
        criteria: dict | None = None,
    ):
        self.data_provider = data_provider
        self.criteria = {**self.DEFAULT_CRITERIA, **(criteria or {})}

    def filter(self, tickers: list[str]) -> list[str]:
        """Subset of tickers that meets EVERY criterion."""
        fundamentals = self.data_provider.get_fundamentals(tickers)
        return [
            t for t in tickers
            if self._passes(fundamentals[fundamentals["ticker"] == t])
        ]

    def _passes(self, df: pd.DataFrame) -> bool:
        c = self.criteria
        return (
            self._debt_to_equity_ok(df, c["max_debt_to_equity"])
            and self._operating_margin_ok(
                df, c["min_operating_margin"], c["operating_margin_years"]
            )
        )

    def _debt_to_equity_ok(self, df: pd.DataFrame, threshold: float) -> bool:
        """debtToEquity of the last available year <= threshold. Missing data -> discard."""
        dte = df[df["metric"] == "debtToEquity"]
        if dte.empty:
            return False
        last = dte.loc[dte["year"].idxmax(), "value"]
        return last <= threshold

    def _operating_margin_ok(
        self, df: pd.DataFrame, threshold: float, years: int
    ) -> bool:
        """operatingMargins >= threshold in each of the last ``years``.

        If there is less than ``years`` years of data, the ticker is discarded.
        """
        om = df[df["metric"] == "operatingMargins"].nlargest(years, "year")
        if len(om) < years:
            return False
        return bool((om["value"] >= threshold).all())
