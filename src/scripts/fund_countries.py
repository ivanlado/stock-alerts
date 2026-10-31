"""Fetches the country split of every fund in ``data/funds.json`` from justETF.

Run by hand, from ``src/``::

    python -m scripts.fund_countries

Writes ``data/fund_countries.json``: ``{"as_of": <date>, "funds": {ticker:
[{"country", "weight"}, ...]}}``, weights in percent. justETF lists the four
largest countries and groups the rest as "Other".

WHY A MANUAL SCRIPT. Neither yfinance nor iShares offers the split by country
any more, and justETF has no API: this reads its public ETF page. Scraping it
from the daily job would hit the site every day and break the run the day the
page changes. A country split moves a point or two a year, so it is fetched
now and then by hand and the date travels with it, for the web to show.
"""

import html
import json
import re
from datetime import date
from pathlib import Path

import requests

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
FUNDS_PATH = DATA_DIR / "funds.json"
OUT_PATH = DATA_DIR / "fund_countries.json"

# justETF finds a fund by its ISIN, not by its Xetra ticker. A fund added to
# ``data/funds.json`` needs its ISIN here too; one that is missing is reported.
ISINS = {
    "SXR8.DE": "IE00B5BMR087",  # iShares Core S&P 500 UCITS ETF (Acc)
    "EUNL.DE": "IE00B4L5Y983",  # iShares Core MSCI World UCITS ETF (Acc)
    "IUSQ.DE": "IE00B6R52259",  # iShares MSCI ACWI UCITS ETF (Acc)
    "IS3N.DE": "IE00BKM4GZ66",  # iShares Core MSCI EM IMI UCITS ETF (Acc)
    "SXRV.DE": "IE00B53SZB19",  # iShares NASDAQ 100 UCITS ETF (Acc)
    "EXW1.DE": "DE0005933956",  # iShares Core EURO STOXX 50 UCITS ETF (DE)
}

PAGE_URL = "https://www.justetf.com/en/etf-profile.html?isin={isin}"

# Each country row on the page carries these two test ids, name first.
ROW = re.compile(
    r'tl_etf-holdings_countries_value_name">([^<]+)<.*?'
    r'tl_etf-holdings_countries_value_percentage">([\d.,]+)%',
    re.S,
)


def fetch_countries(isin: str) -> list[dict]:
    """``[{"country": "United States", "weight": 70.32}, ...]`` for one fund."""
    response = requests.get(
        PAGE_URL.format(isin=isin), headers={"User-Agent": "Mozilla/5.0"}, timeout=30
    )
    response.raise_for_status()
    return [
        {"country": html.unescape(name).strip(), "weight": float(weight.replace(",", ""))}
        for name, weight in ROW.findall(response.text)
    ]


def main() -> None:
    funds = json.loads(FUNDS_PATH.read_text())
    result: dict[str, list[dict]] = {}
    for ticker in funds:
        isin = ISINS.get(ticker)
        if isin is None:
            print(f"{ticker}: no ISIN in ISINS, skipped")
            continue
        try:
            countries = fetch_countries(isin)
        except Exception as e:
            print(f"{ticker}: {type(e).__name__}: {e}")
            continue
        if not countries:
            # The page loaded but held no country rows: most likely justETF
            # changed its markup and ROW needs updating.
            print(f"{ticker}: no countries found on the page")
            continue
        result[ticker] = countries
        print(f"{ticker}: " + ", ".join(f"{c['country']} {c['weight']}%" for c in countries))

    payload = {"as_of": date.today().isoformat(), "funds": result}
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({len(result)} of {len(funds)} funds)")


if __name__ == "__main__":
    main()
