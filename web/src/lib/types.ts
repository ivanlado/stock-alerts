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

/** analyst_alerts.json */
export type AnalystAlert = {
  ticker: string;
  short_name: string | null;
  current: number | null;
  median: number | null;
  price_diff: number | null;
  pct_price_diff: number | null;
};

/** price_alerts.json */
export type PriceAlert = {
  ticker: string;
  short_name: string | null;
  date: string;
  close: number | null;
  var_1m: number | null;
  var_3m: number | null;
  var_6m: number | null;
  var_9m: number | null;
};

/** screener.json */
export type ScreenerRow = {
  ticker: string;
  short_name: string | null;
};
