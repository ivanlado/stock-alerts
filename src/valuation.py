"""Price-based ratios, year by year.

Every other fundamental in the project comes out of the accounts alone, so one
number per period falls straight out of a statement. These two do not: a PER
and a price/sales ratio need a PRICE, and a price only means something at a
date. So they are computed here, where the pipeline has both the statements
and the five years of daily closes, instead of in the provider -- which caches
its CSVs for the whole universe and would otherwise have to cache a number
that goes stale the next morning.

    PER(year)          = close at that year end / diluted EPS of that year
    price/sales(year)  = close at that year end * diluted shares / revenue

The price used is the last close of the calendar year, not of the fiscal year:
yfinance labels every period by its calendar year already (see
``_period_label``), and matching a company's own fiscal calendar would mean
carrying the statement dates around for a difference of a few weeks on a
number that is read as an order of magnitude.

Only the annual table gets these. A quarter's EPS is a quarter's earnings, so
dividing a price by it gives roughly four times the real PER -- a number that
looks like a fact and is not one.

TODAY's pair is computed here too, and from the same two sources: the last
close of the price history and the last twelve months of the statements.
yfinance publishes a ready-made ``trailingPE`` in ``info`` and it is NOT used,
because it disagrees with its own accounts: for AENA.MC it reports an EPS of
6.07 against a 26.26 price (a PER of 4.3) while the income statement of the
same ticker reports 1.42 (a PER of 18.5, the plausible one). A number that
contradicts the rest of the card is worse than one we can account for.
"""

import pandas as pd

# What the computed rows are called in the long-form table, alongside
# ``operatingMargins`` and the rest. camelCase like the other computed ratios.
PRICE_EARNINGS = "priceEarnings"
PRICE_TO_SALES = "priceToSales"


def _year_end_closes(prices: pd.DataFrame) -> dict[tuple[str, int], float]:
    """``{(ticker, year): last close of that year}``.

    ``prices`` is the long-form table the pipeline already downloads
    (ticker, date, open, high, low, close, volume).
    """
    if prices.empty:
        return {}

    df = prices[["ticker", "date", "close"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    # The last row of each (ticker, year) once sorted by date is that year's
    # closing price. `idxmax` on the date would do the same; sorting keeps it
    # readable.
    df = df.sort_values("date")
    last = df.groupby(["ticker", "year"]).last()
    return {
        (str(ticker), int(year)): float(close)
        for (ticker, year), close in last["close"].items()
        if pd.notna(close)
    }


def _quarter_index(period: str) -> int | None:
    """"2026Q2" -> a running quarter number, so two periods can be compared."""
    try:
        year, quarter = str(period).split("Q")
        return int(year) * 4 + int(quarter)
    except (ValueError, AttributeError):
        return None


def _trailing_window(periods: list[str]) -> list[str]:
    """The periods of ``periods`` that fall in the last twelve months.

    Taking "the last four rows" would be wrong: a company reporting twice a
    year -- which several on the Spanish side do -- would hand back two full
    years and halve its PER. So the window is measured in quarters from the
    most recent period, and whatever the company filed inside it is what gets
    summed, be that four quarters or two halves.
    """
    indexed = [(p, _quarter_index(p)) for p in periods]
    indexed = [(p, i) for p, i in indexed if i is not None]
    if not indexed:
        return []
    latest = max(i for _, i in indexed)
    return [p for p, i in indexed if latest - 3 <= i <= latest]


def _pivot(table: pd.DataFrame) -> dict[tuple[str, int], dict[str, float]]:
    """Long-form (ticker, year, metric, value) -> ``{(ticker, year): {metric: value}}``."""
    out: dict[tuple[str, int], dict[str, float]] = {}
    if table.empty or "year" not in table.columns:
        return out
    for ticker, year, metric, value in zip(
        table["ticker"], table["year"], table["metric"], table["value"]
    ):
        if pd.isna(value):
            continue
        try:
            key = (str(ticker), int(year))
        except (TypeError, ValueError):
            continue
        out.setdefault(key, {})[str(metric)] = float(value)
    return out


def valuation_history(
    valuation_inputs: pd.DataFrame,
    fundamentals: pd.DataFrame,
    prices: pd.DataFrame,
) -> pd.DataFrame:
    """The two ratios per (ticker, year), in the same long form as the rest.

    The result is meant to be concatenated onto the annual fundamentals, so a
    sink sees them as two more metrics and needs to know nothing about how
    they were built.

    A year with no price (the history only goes back five), no EPS, or a
    denominator of zero simply produces no row: a missing cell is honest,
    whereas a PER on a loss-making year is arithmetic rather than information.
    Negative EPS is left as a negative PER, which is the convention.
    """
    columns = ["ticker", "year", "metric", "value"]
    closes = _year_end_closes(prices)
    if not closes:
        return pd.DataFrame(columns=columns)

    inputs = _pivot(valuation_inputs)
    revenues = _pivot(fundamentals)

    rows: list[dict] = []
    for key, metrics in inputs.items():
        close = closes.get(key)
        if close is None:
            continue
        ticker, year = key

        eps = metrics.get("Diluted EPS")
        if eps is not None and eps != 0:
            rows.append({
                "ticker": ticker, "year": year,
                "metric": PRICE_EARNINGS, "value": close / eps,
            })

        shares = metrics.get("Diluted Average Shares")
        revenue = revenues.get(key, {}).get("Total Revenue")
        if shares and revenue:
            rows.append({
                "ticker": ticker, "year": year,
                "metric": PRICE_TO_SALES, "value": close * shares / revenue,
            })

    return pd.DataFrame(rows, columns=columns)


def _last_closes(prices: pd.DataFrame) -> dict[str, float]:
    """``{ticker: most recent close}`` -- the price the card itself shows."""
    if prices.empty:
        return {}
    df = prices[["ticker", "date", "close"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    last = df.sort_values("date").groupby("ticker").last()
    return {
        str(ticker): float(close)
        for ticker, close in last["close"].items()
        if pd.notna(close)
    }


def _trailing_totals(quarterly: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Each ticker's last twelve months, metric by metric.

    Only sums the periods `_trailing_window` keeps, and only when every one of
    them reports the metric: a year missing a quarter would understate the
    total and overstate nothing visible, which is the kind of wrong number
    that gets believed.

    Everything here is summed, so only FLOW metrics (earnings, revenue) may be
    read off the result. A balance such as the share count must not be.
    """
    totals: dict[str, dict[str, float]] = {}
    if quarterly.empty or "period" not in quarterly.columns:
        return totals

    for ticker, rows in quarterly.groupby("ticker"):
        window = set(_trailing_window(sorted({str(p) for p in rows["period"]})))
        if not window:
            continue
        inside = rows[rows["period"].astype(str).isin(window)]
        per_metric: dict[str, list[float]] = {}
        for metric, period, value in zip(
            inside["metric"].astype(str), inside["period"].astype(str), inside["value"]
        ):
            if pd.notna(value):
                per_metric.setdefault(metric, []).append(float(value))
        totals[str(ticker)] = {
            metric: sum(values)
            for metric, values in per_metric.items()
            if len(values) == len(window)
        }
    return totals


def _latest_annual(table: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Each ticker's most recent reported year, metric by metric."""
    latest: dict[str, dict[str, float]] = {}
    if table.empty or "year" not in table.columns:
        return latest
    for (ticker, year), metrics in _pivot(table).items():
        known = latest.setdefault(ticker, {"__year": -1})
        if year > known["__year"]:
            latest[ticker] = {"__year": year, **metrics}
    return latest


def valuation_today(
    prices: pd.DataFrame,
    quarterly: pd.DataFrame,
    valuation_inputs: pd.DataFrame,
    fundamentals: pd.DataFrame,
) -> pd.DataFrame:
    """Today's PER and price/sales: (ticker, trailing_pe, price_to_sales).

    The price is the last close of the history the chart already draws, so
    these can never contradict the price shown beside them. The earnings and
    sales are the last twelve months when the company files quarterly, and its
    most recent full year when it does not -- the fallback is what makes this
    work for the tickers that report twice a year.

    A company with no earnings, or whose statements are too sparse to add up,
    gets None rather than a number: the card greys the badge out.
    """
    closes = _last_closes(prices)
    if not closes:
        return pd.DataFrame(columns=["ticker", "trailing_pe", "price_to_sales"])

    ttm = _trailing_totals(quarterly)
    annual_inputs = _latest_annual(valuation_inputs)
    annual_figures = _latest_annual(fundamentals)

    rows = []
    for ticker, close in closes.items():
        trailing = ttm.get(ticker, {})
        inputs = annual_inputs.get(ticker, {})
        figures = annual_figures.get(ticker, {})

        eps = trailing.get("Diluted EPS") or inputs.get("Diluted EPS")
        revenue = trailing.get("Total Revenue") or figures.get("Total Revenue")
        # NOT taken from the trailing totals: a share count is a balance, not
        # a flow, so adding four quarters of it would quadruple the company.
        # The annual figure barely moves year to year anyway.
        shares = inputs.get("Diluted Average Shares")

        rows.append({
            "ticker": ticker,
            "trailing_pe": close / eps if eps else None,
            "price_to_sales": close * shares / revenue if shares and revenue else None,
        })

    return pd.DataFrame(rows, columns=["ticker", "trailing_pe", "price_to_sales"])
