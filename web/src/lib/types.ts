/**
 * Shape of the JSON files produced by `src/export/json_export.py`.
 *
 * WHY THIS FILE EXISTS. TypeScript checks types before the app runs. Describing
 * the data here means that renaming a column in Python and forgetting to update
 * the frontend produces a compile error instead of a blank cell in production.
 *
 * `type X = { ... }` declares the shape of an object. `string | null` means
 * "a string OR null" -- Python writes null wherever a value is missing.
 * `<Row>` in `Payload` is a generic: a placeholder filled in at each use,
 * so `Payload<AnalystAlert>` is a payload whose rows are analyst alerts.
 */

/** Wrapper shared by every file: { generated_at, rows }. */
export type Payload<Row> = {
  generated_at: string;
  rows: Row[];
};

/**
 * What every row knows about the company behind it, from `data/tickers.csv`.
 *
 * `description` is Yahoo's own business summary. Unlike the LLM commentary it
 * is present for every ticker, so it is what the UI falls back to.
 *
 * The types below are written as `Company & { ... }`. The `&` is an
 * intersection: a value having the fields of BOTH sides. It saves declaring
 * these fields once per table, and lets a component accept "any row that
 * identifies a company" without caring which table it came from.
 */
export type Company = {
  ticker: string;
  short_name: string | null;
  sector: string | null;
  description: string | null;
};

/**
 * The LLM-written text attached to every alert, from `src/enrichment/`.
 * It is null when the model call failed (a quota, a timeout), so the UI must
 * cope with its absence. It is written in Spanish: it is the only text on the
 * page that is not produced by this code.
 */
export type Commentary = {
  explanation: string | null;
};

/**
 * What the model says a company IS, from `src/enrichment/profiles.py`.
 *
 * Unlike `explanation`, these answers barely change, so Python caches them on
 * disk for months instead of asking again every day. Every field is optional
 * (`?`) and nullable: a section is null when that one call failed, and absent
 * when it was added to the Python prompts after the cache was written.
 */
export type CompanyProfile = {
  summary?: string | null;
  revenue_sources?: string | null;
  moat?: string | null;
  competitors?: string | null;
  threats?: string | null;
  outlook?: string | null;
};

/**
 * prices.json -- the daily close of each alerted company.
 *
 * A point is a `[date, close]` pair rather than an object: this file is mostly
 * points, and repeating two key names thousands of times would double its size
 * for nothing. `[string, number]` is a TUPLE: an array of exactly those two
 * types, in that order.
 */
export type PriceSeries = {
  ticker: string;
  points: [string, number][];
};

/** analyst_alerts.json */
export type AnalystAlert = Company &
  Commentary & {
    current: number | null;
    median: number | null;
    price_diff: number | null;
    pct_price_diff: number | null;
  };

/** price_alerts.json */
export type PriceAlert = Company &
  Commentary & {
    date: string;
    close: number | null;
    var_1m: number | null;
    var_3m: number | null;
    var_6m: number | null;
    var_9m: number | null;
  };

/**
 * One period of a company's fundamentals.
 *
 * `period` is a year ("2025") for the annual table and a quarter ("2025Q3")
 * for the quarterly one -- the same shape either way, so one component renders
 * both. It is a string rather than a number so those two formats can share it,
 * and because both sort chronologically as text.
 *
 * The first three are the ratios the Python screener filters on, which is why
 * they are the ones the cards lead with. `operating_margin` arrives already
 * converted to a percentage; the money figures are in the company's reporting
 * currency and are shown compacted (44.3B).
 */
export type Fundamentals = {
  period: string;
  operating_margin: number | null;
  debt_to_equity: number | null;
  current_ratio: number | null;
  total_revenue: number | null;
  cost_of_revenue: number | null;
  ebitda: number | null;
  free_cash_flow: number | null;
};

/**
 * companies.json -- one row per SCREENED company, with BOTH rules' numbers.
 *
 * Every company that passed the fundamental filters is here, alert or not, so
 * the dashboard shows the whole shortlist rather than only today's noise.
 * `analyst_alert` and `price_alert` say which rule fired, if any -- that is
 * what the card badges -- and the rows that fired come first.
 */
export type CompanyCard = Company &
  Commentary & {
    current: number | null;
    median: number | null;
    pct_price_diff: number | null;
    var_1m: number | null;
    var_3m: number | null;
    var_6m: number | null;
    var_9m: number | null;
    /** Which of the two rules fired for this company. Both false is normal. */
    analyst_alert: boolean;
    price_alert: boolean;
    /** The cached LLM profile, or null when the company has none yet. */
    profile: CompanyProfile | null;
    /** The most recent reported year, or null when the company has no data. */
    fundamentals: Fundamentals | null;
    /** Every reported year, oldest first. Empty when there is no data. */
    fundamentals_history: Fundamentals[];
    /**
     * The same metrics quarter by quarter, oldest first. Empty when Yahoo
     * publishes no quarterly statements for the company, which happens: not
     * every market requires them.
     */
    fundamentals_quarterly: Fundamentals[];
  };

/** screener.json */
export type ScreenerRow = {
  ticker: string;
  short_name: string | null;
  sector: string | null;
};
