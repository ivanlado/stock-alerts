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
 * The two LLM-written texts attached to every alert, from `src/enrichment/`.
 * Both are null when the model call failed (a quota, a timeout), so the UI
 * must cope with their absence.
 */
export type Commentary = {
  business: string | null;
  explanation: string | null;
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
 * One year of a company's fundamentals, from `data/fundamentals.csv`.
 *
 * The first three are the ratios the Python screener filters on, which is why
 * they are the ones the cards lead with. `operating_margin` arrives already
 * converted to a percentage; the money figures are in the company's reporting
 * currency and are shown compacted (44.3B).
 */
export type Fundamentals = {
  year: number;
  operating_margin: number | null;
  debt_to_equity: number | null;
  current_ratio: number | null;
  total_revenue: number | null;
  cost_of_revenue: number | null;
  ebitda: number | null;
  free_cash_flow: number | null;
};

/**
 * companies.json -- one row per ALERTED company, merging both alert tables.
 *
 * A company that fired only one of the two rules has nulls in the other
 * rule's columns: there is no 1-month variation for a ticker that only
 * triggered the analyst rule. The cards grey those out rather than hiding
 * them, so the shape of a card stays the same for every company.
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
    /** The most recent reported year, or null when the company has no data. */
    fundamentals: Fundamentals | null;
    /** Every reported year, oldest first. Empty when there is no data. */
    fundamentals_history: Fundamentals[];
  };

/** screener.json */
export type ScreenerRow = {
  ticker: string;
  short_name: string | null;
  sector: string | null;
};
