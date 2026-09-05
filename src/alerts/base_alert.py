from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

import pandas as pd

from providers.base import DataProvider


class BaseAlert(ABC):
    """Base class for alert rules.

    Subclasses only implement ``apply_rules``, which returns the rows that
    trigger the alert as a DataFrame. Formatting for a specific output
    (email, JSON, ...) is NOT done here: it belongs to the consumer.
    """

    def __init__(self, tickers: List[str], data_provider: DataProvider):
        if not tickers:
            raise ValueError("tickers cannot be empty")

        self.tickers = tickers
        self.data_provider = data_provider
        data_dir = Path(__file__).resolve().parents[2] / "data"
        self.tickers_info = pd.read_csv(data_dir / "tickers.csv")

    @abstractmethod
    def apply_rules(self) -> pd.DataFrame:
        """Rows matching the alert rule. One row per triggering ticker."""
        raise NotImplementedError

    def run(self) -> pd.DataFrame:
        """Alert rows enriched with the ticker's display name."""
        return self._with_names(self.apply_rules())

    def _with_names(self, alerts: pd.DataFrame) -> pd.DataFrame:
        """Adds ``short_name`` to the alert rows, keeping the CSV's extra columns out."""
        names = self.tickers_info[["ticker", "short_name"]]
        return alerts.merge(names, on="ticker", how="left")
