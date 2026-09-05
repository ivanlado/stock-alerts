"""Data pipeline: from raw tickers to a Snapshot of results.

This module has no side effects (no emails, no files). It only computes data,
so any consumer -- email, JSON export, web -- can format it as it needs.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd

from alerts.analysts_alert import AnalystAlerts
from alerts.price_alerts import PriceAlert
from providers import DataProviderImpl
from screening import FundamentalScreener

# Kept from the previous main.py: caps how many screened tickers reach the
# alert stage. Set to None to process all of them.
DEFAULT_TICKER_LIMIT = 20


@dataclass
class Snapshot:
    """Result of a single run of the pipeline."""

    generated_at: datetime
    screened: list[str]
    analyst_alerts: pd.DataFrame
    price_alerts: pd.DataFrame

    @property
    def has_alerts(self) -> bool:
        return not self.analyst_alerts.empty or not self.price_alerts.empty


def run_pipeline(limit: int | None = DEFAULT_TICKER_LIMIT) -> Snapshot:
    """Loads tickers, screens them by fundamentals and runs every alert rule."""
    generated_at = datetime.now(timezone.utc)

    data_provider = DataProviderImpl()
    tickers = data_provider.get_tickers()
    print(f"Number of tickers: {len(tickers)}")

    screener = FundamentalScreener(data_provider)
    screened = screener.filter(tickers)
    if limit is not None:
        screened = screened[:limit]
    print(f"Tickers after fundamental screening: {len(screened)} -> {screened}")

    if not screened:
        return Snapshot(
            generated_at=generated_at,
            screened=[],
            analyst_alerts=pd.DataFrame(),
            price_alerts=pd.DataFrame(),
        )

    return Snapshot(
        generated_at=generated_at,
        screened=screened,
        analyst_alerts=AnalystAlerts(screened, data_provider=data_provider).run(),
        price_alerts=PriceAlert(screened, data_provider=data_provider).run(),
    )
