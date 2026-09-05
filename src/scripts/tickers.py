"""
tickers.py
==========
Functions that fetch the tickers of stock market indices from Wikipedia.

Meant to be imported from another module:

    from scripts.tickers import get_tickers, scrape_tickers

    sp500 = get_tickers("sp500")        # by name (uses the INDICES registry)
    ibex  = get_tickers("ibex35")

    # or straight from a URL, without touching the registry:
    others = scrape_tickers(
        "https://es.wikipedia.org/wiki/FTSE_100",
        ticker_headers=["ticker", "símbolo", "epic"],
        expected_rows=100,
    )

Requirements:
    pip install pandas lxml requests
"""

from __future__ import annotations

from io import StringIO

import pandas as pd
import requests

# Wikipedia returns 403 without a real browser User-Agent.
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

# Registry of known indices. Add the ones you need here.
# The values in "ticker_headers" are data, not prose: they must match the
# column headings of the Spanish Wikipedia pages being scraped, so they stay
# in Spanish.
INDICES: dict[str, dict] = {
    "sp500": {
        "url": "https://es.wikipedia.org/wiki/Anexo:Compa%C3%B1%C3%ADas_del_S%26P_500",
        "ticker_headers": ["símbolo", "simbolo", "symbol", "ticker"],
        "expected_rows": 503,
    },
    "ibex35": {
        "url": "https://es.wikipedia.org/wiki/IBEX_35",
        "ticker_headers": ["ticker", "símbolo", "simbolo", "código", "codigo"],
        "expected_rows": 35,
        "suffix": ".MC",
    },
}


def scrape_tickers(
    url: str,
    ticker_headers: list[str],
    expected_rows: int | None = None,
    timeout: int = 30,
    suffix: str | None = None,
) -> list[str]:
    """Downloads a Wikipedia page and returns the list of tickers.

    Parameters
    ----------
    url:
        Exact link to the Wikipedia page.
    ticker_headers:
        Possible names (lowercase) of the ticker column. Compared with
        startswith(), so "símbolo" also covers "símbolo bursátil", etc.
    expected_rows:
        Approximate number of constituents. Breaks the tie when several tables
        have a ticker column (e.g. the composition table against a table of
        historical changes).
    timeout:
        Seconds to wait for the HTTP request.

    Returns
    -------
    list[str]
        The tickers, already cleaned (no footnotes, no whitespace).

    Raises
    ------
    requests.HTTPError
        If the download fails.
    ValueError
        If no ticker column is found.
    """
    resp = requests.get(url, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()
    tables = pd.read_html(StringIO(resp.text))

    table, ticker_col = _find_ticker_table(tables, ticker_headers, expected_rows)
    tickers = _clean_tickers(table[ticker_col])
    if suffix:
        tickers = [t + suffix for t in tickers]
    return tickers


def get_tickers(index_name: str) -> list[str]:
    """Returns the tickers of an index registered in INDICES.

    Example: get_tickers("sp500") -> ["MMM", "AOS", ...]
    """
    if index_name not in INDICES:
        available = ", ".join(INDICES)
        raise KeyError(
            f"'{index_name}' is not in INDICES. Available: {available}"
        )
    cfg = INDICES[index_name]
    return scrape_tickers(
        cfg["url"],
        ticker_headers=cfg["ticker_headers"],
        expected_rows=cfg.get("expected_rows"),
        suffix=cfg.get("suffix"),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _find_ticker_table(
    tables: list[pd.DataFrame],
    ticker_headers: list[str],
    expected_rows: int | None = None,
) -> tuple[pd.DataFrame, object]:
    """Picks the (table, column) whose heading matches ticker_headers."""
    matches: list[tuple[pd.DataFrame, object]] = []
    for table in tables:
        for col in table.columns:
            name = str(col).strip().lower()
            if any(name.startswith(key) for key in ticker_headers):
                matches.append((table, col))
                break
    if not matches:
        raise ValueError("No ticker column found.")
    if expected_rows is not None:
        matches.sort(key=lambda m: abs(len(m[0]) - expected_rows))
    return matches[0]


def _clean_tickers(series: pd.Series) -> list[str]:
    """Strips footnotes [1], whitespace and empty/NaN cells."""
    cleaned = (
        series.astype(str)
        .str.replace(r"\[.*?\]", "", regex=True)
        .str.strip()
    )
    return [t for t in cleaned.tolist() if t and t.lower() != "nan"]
