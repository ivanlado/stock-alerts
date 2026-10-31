"""Data pipeline: from raw tickers to a Snapshot of results.

This module has no side effects (no emails, no files). It only computes data,
so any consumer -- email, JSON export, web -- can format it as it needs.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd

from alerts.analysts_alert import AnalystAlerts
from alerts.price_alerts import PriceAlert
from enrichment import add_commentary, get_profiles
from enrichment import prompts
from providers import DataProviderImpl
from screening import FundamentalScreener
from valuation import valuation_history, valuation_today

# Caps how many screened tickers reach the alert stage. None processes all of
# them; a number is handy while testing, to keep a local run short.
DEFAULT_TICKER_LIMIT = None

# How far back the price history goes. The price rule needs more than a year
# for its longest window, and the web chart offers a five-year view, so one
# download covers both.
PRICE_HISTORY_PERIOD = "5y"


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
    # The same metrics quarter by quarter (ticker, period, metric, value), for
    # the recent trend. Nothing filters on these: the screener works on the
    # annual figures, which are the audited ones.
    fundamentals_quarterly: pd.DataFrame = field(default_factory=pd.DataFrame)
    # The same two rules computed for EVERY screened ticker, whether it alerted
    # or not. A company card shows both rules for every company on it, and a
    # ticker that only fired the price rule still has a gap to its analyst
    # target -- it just was not wide enough to alert on.
    analyst_all: pd.DataFrame = field(default_factory=pd.DataFrame)
    price_all: pd.DataFrame = field(default_factory=pd.DataFrame)
    # Index funds and ETFs (``data/funds.json``). They have no statements and
    # no analyst targets, so they skip the screener and the analyst rule and
    # only go through the price rule: their rows sit in ``price_all`` and, when
    # they fire, in ``price_alerts``, next to the companies'.
    funds: list[str] = field(default_factory=list)
    # ``{ticker: {"expense_ratio", "top_holdings", "sectors"}}`` per fund: what
    # the fund holds, for its detail panel. Only the top ten holdings, which
    # is all the source publishes.
    fund_details: dict[str, dict] = field(default_factory=dict)
    # Daily closes of the screened tickers and the funds, for the chart on the web.
    prices: pd.DataFrame = field(default_factory=pd.DataFrame)
    # ``{ticker: profile}`` -- the cached LLM description of each screened
    # company. See ``enrichment/profiles.py``.
    profiles: dict[str, dict] = field(default_factory=dict)
    # Today's PER and price/sales per ticker (ticker, trailing_pe,
    # price_to_sales). Trailing twelve months against the CURRENT price, so
    # unlike everything above they belong to no period: they are the headline
    # number on a card, while ``fundamentals`` carries the year-by-year series
    # of the same two ratios.
    valuation: pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def has_alerts(self) -> bool:
        return not self.analyst_alerts.empty or not self.price_alerts.empty


def run_pipeline(
    limit: int | None = DEFAULT_TICKER_LIMIT,
    commentary: bool = True,
) -> Snapshot:
    """Loads tickers, screens them by fundamentals and runs every alert rule.

    ``commentary`` adds the LLM-written text: one call per alerted row for
    today's explanation, plus the cached company profile, which only costs
    calls the first time a company is seen (see ``enrichment/profiles.py``).
    Worth turning off while testing the rules themselves.
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

    funds = data_provider.get_funds()
    print(f"Funds watched for price drops: {len(funds)} -> {funds}")
    fund_details = data_provider.get_fund_details(funds)

    # Downloaded once and reused: the price rule needs it to compute its
    # windows, and the web needs the same series for the chart on each card.
    # One request for companies and funds alike.
    prices = data_provider.get_prices(
        screened + funds, period=PRICE_HISTORY_PERIOD, interval="1d"
    )

    # Only for the screened tickers: nothing filters on the quarterly figures,
    # they are there for the company cards.
    fundamentals_quarterly = data_provider.get_quarterly_fundamentals(screened)

    # The PER and price/sales series, computed rather than fetched: they need a
    # price per year, which is why they cannot live in the fundamentals cache
    # (see valuation.py). Appended to the annual table so every sink sees them
    # as two more metrics.
    screened_fundamentals = fundamentals[fundamentals["ticker"].isin(screened)]
    valuation_inputs = data_provider.get_valuation_inputs(screened)
    history = valuation_history(valuation_inputs, screened_fundamentals, prices)
    if not history.empty:
        screened_fundamentals = pd.concat([screened_fundamentals, history], ignore_index=True)

    # The same two ratios against TODAY's price and the last twelve months.
    # Computed from the price history and the statements already in hand, not
    # fetched: yfinance's own ``trailingPE`` contradicts its own accounts for
    # some tickers (see valuation.py), and a number that disagrees with the
    # price printed next to it is worse than no number.
    valuation = valuation_today(
        prices, fundamentals_quarterly, valuation_inputs, screened_fundamentals
    )

    analyst = AnalystAlerts(screened, data_provider=data_provider)
    price = PriceAlert(screened + funds, data_provider=data_provider, prices=prices)

    analyst_alerts, analyst_all = analyst.run(), analyst.run_all()
    price_alerts, price_all = price.run(), price.run_all()

    if commentary:
        analyst_alerts = add_commentary(analyst_alerts, prompts.ANALYST_DIVERGENCE)
        price_alerts = add_commentary(price_alerts, prompts.PRICE_DROP)

    # The web shows a card per SCREENED company, not just per alerted one, so
    # the profile and the price series are wanted for all of them.
    profiles = get_profiles(_display_names(screened, analyst_all, price_all)) if commentary else {}

    return Snapshot(
        generated_at=generated_at,
        screened=screened,
        funds=funds,
        fund_details=fund_details,
        analyst_alerts=analyst_alerts,
        price_alerts=price_alerts,
        fundamentals=screened_fundamentals,
        fundamentals_quarterly=fundamentals_quarterly,
        analyst_all=analyst_all,
        price_all=price_all,
        prices=prices,
        profiles=profiles,
        valuation=valuation,
    )


def _display_names(
    tickers: list[str], *tables: pd.DataFrame
) -> dict[str, str]:
    """``{ticker: short_name}``, falling back to the ticker itself.

    The name is what the LLM is asked about ("what does Agilent do?"), so it
    is worth looking for in whichever table happens to carry it.
    """
    names: dict[str, str] = {}
    for table in tables:
        if table.empty or "short_name" not in table.columns:
            continue
        for ticker, name in zip(table["ticker"].astype(str), table["short_name"]):
            if ticker in tickers and isinstance(name, str) and name:
                names.setdefault(ticker, name)
    return {ticker: names.get(ticker, ticker) for ticker in tickers}
