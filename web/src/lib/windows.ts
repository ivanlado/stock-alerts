import type { PriceVariations } from "./types";

/**
 * The price rule's time windows, shortest first, with the label shown for each.
 *
 * Declared once so the window buttons, the card badges and the detail panel
 * cannot disagree on a label. `key` is restricted to the keys of
 * PriceVariations, so a window Python does not export is a compile error.
 * The thresholds that make each window fire live in Python
 * (`THRESHOLDS` in `src/alerts/price_alerts.py`); the web only shows numbers.
 */
export type PriceWindowKey = keyof PriceVariations;

export const PRICE_WINDOWS: { key: PriceWindowKey; label: string }[] = [
  { key: "var_1d", label: "1D" },
  { key: "var_1w", label: "1W" },
  { key: "var_1m", label: "1M" },
  { key: "var_3m", label: "3M" },
  { key: "var_6m", label: "6M" },
  { key: "var_9m", label: "9M" },
  { key: "var_1y", label: "1Y" },
];

/** The window the Price drops page and the summary rank by. */
export const DEFAULT_WINDOW: PriceWindowKey = "var_3m";

/** The label of a window, e.g. "3M". */
export function windowLabel(key: PriceWindowKey): string {
  return PRICE_WINDOWS.find((w) => w.key === key)?.label ?? key;
}
