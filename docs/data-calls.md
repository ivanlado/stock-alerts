# Data calls

What the pipeline downloads, and how often. Per-company calls are spaced
0.1–0.7 s apart (`src/providers/yfinance_provider.py`).

## Every day (not cached)

| Data | Call | Calls |
|---|---|---|
| Daily prices (5 years) | `yf.download([...])` | **1**, batched |
| Analyst price target | `Ticker(t).analyst_price_targets` | **1 per company** (~540, the whole universe, for Search) — the real daily cost |
| Fund data (TER, holdings, sectors) | `Ticker(t).funds_data` | 1 per fund (6). Could be cached |
| LLM: today's explanation | Gemini | 1 per alert, capped at 20/day (free tier) |

## Once per company (cached)

| Data | Call | Cache |
|---|---|---|
| Annual fundamentals | annual statements | `data/fundamentals.csv` |
| Quarterly fundamentals | quarterly statements | `data/fundamentals_quarterly.csv` |
| EPS and share count (PER, P/S) | `Ticker(t).financials` | `data/valuation_inputs.csv` |
| LLM: company profile | Gemini | `HISTORY_DIR/profiles/`, refreshed after 90 days |

The statement caches are **never refreshed**: a new annual report is ignored
until the file is deleted.

## By hand (scripts, outside the daily job)

| Data | Source | Output |
|---|---|---|
| Catalog (name, sector, description) | `Ticker(t).info` | `data/tickers.csv` |
| Fund country split | justETF, 1 per fund | `data/fund_countries.json` |

## Why per company

Yahoo only batches prices. Statements and price targets are one call per
ticker. A batch quote endpoint exists, but its EPS is the `info.trailingPE`
figure that contradicts the companies' own accounts, so it is not used.
