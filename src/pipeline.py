"""Data pipeline: from raw tickers to a Snapshot of results.

This module has no side effects (no emails, no files). It only computes data,
so any consumer -- email, JSON export, web -- can format it as it needs.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd

from alerts.analysts_alert import AnalystAlerts
from alerts.price_alerts import PriceAlert
from enrichment import add_commentary
from enrichment import prompts
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
    # Long-form table (ticker, year, metric, value) for the screened tickers.
    # Kept on the Snapshot so a sink can show WHY a company passed the filters,
    # not just that it did.
    fundamentals: pd.DataFrame

    @property
    def has_alerts(self) -> bool:
        return not self.analyst_alerts.empty or not self.price_alerts.empty


def run_pipeline(
    limit: int | None = DEFAULT_TICKER_LIMIT,
    commentary: bool = True,
) -> Snapshot:
    """Loads tickers, screens them by fundamentals and runs every alert rule.

    ``commentary`` adds the LLM-written columns to the alerts. It costs two API
    calls per alerted company, so it is worth turning off while testing the
    rules themselves.
    """
    generated_at = datetime.now(timezone.utc)

    data_provider = DataProviderImpl()
    tickers = data_provider.get_tickers()
    print(f"Number of tickers: {len(tickers)}")

    # Fetched once and handed to the screener, which would otherwise fetch it
    # again on its own.
    fundamentals = data_provider.get_fundamentals(tickers)

    screener = FundamentalScreener(data_provider)
    screened = screener.filter(tickers, fundamentals)
    if limit is not None:
        screened = screened[:limit]
    print(f"Tickers after fundamental screening: {len(screened)} -> {screened}")

    if not screened:
        return Snapshot(
            generated_at=generated_at,
            screened=[],
            analyst_alerts=pd.DataFrame(),
            price_alerts=pd.DataFrame(),
            fundamentals=pd.DataFrame(),
        )

    analyst_alerts = AnalystAlerts(screened, data_provider=data_provider).run()
    price_alerts = PriceAlert(screened, data_provider=data_provider).run()

    if commentary:
        # One shared cache, so a ticker firing both alerts is described once.
        business_cache: dict[str, str | None] = {}
        analyst_alerts = add_commentary(
            analyst_alerts, prompts.ANALYST_DIVERGENCE, business_cache
        )
        price_alerts = add_commentary(
            price_alerts, prompts.PRICE_DROP, business_cache
        )

    return Snapshot(
        generated_at=generated_at,
        screened=screened,
        analyst_alerts=analyst_alerts,
        price_alerts=price_alerts,
        fundamentals=fundamentals[fundamentals["ticker"].isin(screened)],
    )
