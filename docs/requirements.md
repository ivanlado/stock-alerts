# Functional requirements

What the application must do, as seen by its user. How it is built lives in
`CLAUDE.md`; this file only says what the behaviour is. Every number below is
the value in force today, with the place in the code where it is set.

Keep this file up to date: a change in behaviour (a threshold, a filter, a
default, a page) is not finished until it is written here.

## 1. Daily run

- **R1.1** The system runs once a day at 14:00 mainland Spain time (cron
  `0 12 * * *` UTC in `.github/workflows/schedule.yml`). It can also be
  started by hand from GitHub Actions.
- **R1.2** Every run publishes the dashboard, archives the day (§6) and, only
  when at least one alert fired, sends the email (§5).

## 2. Universe and fundamental screening

- **R2.1** The universe is the tickers listed in `data/tickers/*.json`
  (today: IBEX 35 and S&P 500).
- **R2.2** A company passes the screener when both hold
  (`DEFAULT_CRITERIA` in `src/screening/fundamental_screener.py`):
  - debt to equity of the last reported year ≤ 1.0 (100%);
  - operating margin ≥ 7% in each of the last 3 reported years.

  A company with missing data for a criterion is discarded.
- **R2.3** While the project is in development, only the first 20 companies
  that pass are kept (`DEFAULT_TICKER_LIMIT` in `src/pipeline.py`).
- **R2.4** Only screened companies are evaluated by the alert rules and shown
  on the dashboard, plus the funds of §2.5.

### 2.5 Index funds and ETFs

- **R2.5.1** A fixed list of index ETFs (`data/funds.json`) is watched for
  price drops: S&P 500 (`SXR8.DE`), MSCI World (`EUNL.DE`), MSCI ACWI
  (`IUSQ.DE`), MSCI Emerging Markets IMI (`IS3N.DE`), Nasdaq 100 (`SXRV.DE`)
  and Euro Stoxx 50 (`EXW1.DE`). All are UCITS ETFs quoted in euros on Xetra,
  so a drop already includes the currency move.
- **R2.5.2** Funds skip the screener and the analyst rule (they have no
  statements and no analyst target). They go through the price rule (§3.2)
  with the same thresholds as companies.
- **R2.5.3** Their name and description come from `data/tickers.csv`, with
  sector "Fund". The description is hand-written (Yahoo publishes none for
  these funds).
- **R2.5.4** Every run fetches, per fund, its annual fee (TER), its ten largest
  holdings with their weight, and its weight per sector. Only the top ten are
  available from the source.
- **R2.5.5** Each fund's split by country (the four largest countries plus
  "Other") comes from justETF, fetched by hand with
  `python -m scripts.fund_countries` into `data/fund_countries.json`. It is
  NOT refreshed by the daily run; the date it was fetched is shown with it.

## 3. Alert rules

### 3.1 Analyst target

- **R3.1.1** The gap is `(current price − analysts' median target) / median
  target`, in percent.
- **R3.1.2** The alert fires when the gap is below −10%, i.e. the price is more
  than 10% under the target (`MAX_PCT_DIFF` in `src/alerts/analysts_alert.py`).

### 3.2 Price drop

- **R3.2.1** Each window compares the **last available price** with an earlier
  close:

  | Window | Compared against | Fires below |
  |---|---|---|
  | 1D | the close of the previous session | −5% |
  | 1W | the close 1 week back | −5% |
  | 1M | the close 1 month back | −5% |
  | 3M | the close 3 months back | −10% |
  | 6M | the close 6 months back | −15% |
  | 9M | the close 9 months back | −20% |
  | 1Y | the close 1 year back | −15% |

  Thresholds: `THRESHOLDS` in `src/alerts/price_alerts.py`.
- **R3.2.2** Windows are calendar time: "1 month back" is the last session on
  or before the same date one month earlier (a weekend or holiday falls back to
  the session before it).
- **R3.2.3** At 14:00 in Spain the last price of a European ticker is today's
  session in progress, and that of an American ticker is yesterday's close
  (Wall Street has not opened). In both cases 1D is the move since the previous
  close.
- **R3.2.4** The alert fires when **any** window is below its threshold.
- **R3.2.5** A window whose history does not reach that far has no value and
  never fires.

## 4. Dashboard (web)

Public, published to GitHub Pages by the daily run. All text is in English
except the LLM commentary, which is in Spanish.

### 4.1 Navigation

- **R4.1.1** Four sections in the menu: Summary (home), Analyst alerts,
  Price drops, Search. The current section is highlighted.

### 4.2 Summary (`/`)

- **R4.2.1** Four blocks, in this order: the 5 most undervalued analyst alerts
  (ranked as in §4.3), then the 5 biggest price drops over 1D, over 1W and
  over 6M (ranked as in §4.4 with that window).
- **R4.2.2** A price block lists the companies and funds that fired the price
  rule AND fell over that window; one that rose over it is left out.
- **R4.2.3** Each block has a "See all" link to its full section (for a price
  block, with its window already chosen), with the number of companies.
- **R4.2.4** Cards are compact: name, tags and the numbers, without
  fundamentals or text. A click opens the same detail panel as elsewhere.

### 4.3 Analyst alerts (`/analyst`)

- **R4.3.1** Lists only the companies that fired the analyst rule (§3.1).
- **R4.3.2** Filters:
  - **Sector**: chips, any number selectable; "All" (default) clears the
    choice.
  - **Minimum gap to target**: Any (default), 15%, 20%, 25%, 30%, or Custom
    (any number typed by the user). "Any" already means ≥ 10%, the rule's own
    threshold, so every option is stricter.
- **R4.3.3** Order: most undervalued first (−40%, then −30%, then −20%...).
- **R4.3.4** Cards lead with the gap to target, drawn larger, then 1M and 3M.

### 4.4 Price drops (`/price-drops`)

- **R4.4.1** Lists only the companies and funds that fired the price rule in
  any window (§3.2). Funds carry the sector "Fund", so the sector filter can
  show or hide them.
- **R4.4.2** Filters:
  - **Type**: All (default), Stocks, Funds. The sector chips only offer the
    sectors of the chosen type.
  - **Sector**: as in §4.3.
  - **Window**: 1D, 1W, 1M, 3M (default), 6M, 9M, 1Y.
  - **Minimum drop over the chosen window**: Any (default), 5%, 10%, 15%, 20%,
    or Custom.
- **R4.4.3** With the minimum at "Any", every company that fired is shown,
  including those that fired in a different window from the one chosen.
- **R4.4.4** Order: biggest drop over the chosen window first. Companies with no
  value for that window go last.
- **R4.4.5** Cards lead with the chosen window's variation, drawn larger, then
  the gap to target.

### 4.5 Filters, common to every section

- **R4.5.1** Filters are kept in the URL, so a reload or a shared link shows
  the same view.
- **R4.5.2** The section shows how many companies match out of how many fired,
  and says so when none fired or none matches.

### 4.6 Company card and detail panel

- **R4.6.1** A card shows ticker, name, sector, which rules fired, its badges
  (per section, above), the screening ratios, today's PER and price/sales, and
  a short description.
- **R4.6.2** Clicking a card opens a detail panel with: price and target, the
  gap to target and every price window, today's valuation, the latest
  fundamentals, the price chart (3M / 1Y / 5Y), the LLM summary, today's
  explanation of the move, the company profile (revenue sources, moat,
  competitors, threats, outlook) and the annual / quarterly history.
- **R4.6.3** Price variations are coloured green (up) / red (down) on a fixed
  scale saturating at ±20%. Fundamentals are never coloured.
- **R4.6.4** A fund's card and panel leave out what a fund does not have:
  target, fundamentals, valuation and profile. Instead, the panel shows:
  - just before the price chart, the split by country as ONE stacked bar, each
    country a segment proportional to its weight and labelled inside with its
    name and weight rounded to a whole number (narrow segments show it on
    hover), with the date of that data;
  - below the price chart, the TER, the top ten holdings with their weight
    (and how much of the fund they cover together) and the weight of each
    sector, as neutral bars.
- **R4.6.5** When an LLM text is missing, the card falls back to Yahoo's
  description and the panel says the profile has not been written yet.

### 4.7 Search (`/search`)

- **R4.7.1** Placeholder: lists the screened tickers. Not defined yet.

## 5. Email

- **R5.1** Sent only when at least one alert fired, to `ALERT_TO` (or the
  sender when unset), with subject "Stock alerts".
- **R5.2** One line per analyst alert (price, median target, gap) and one per
  price alert (every window from 1D to 1Y).

## 6. LLM commentary and archive

- **R6.1** Every alerted company gets an explanation of today's number, asked
  on every run.
- **R6.2** Every screened company gets a profile, cached and refreshed every
  90 days (`TTL_DAYS` in `src/enrichment/profiles.py`).
- **R6.3** A failed LLM call leaves the text empty; it never stops the run.
- **R6.4** Every run is archived (screened set, alerts, commentary), including
  the days when nothing fires, so the history can be rebuilt later.
