import { useSearchParams } from "react-router-dom";
import type { Company } from "./types";

/**
 * Filtering and ranking of the company cards, shared by every alert page.
 *
 * Every page answers the same question -- "which companies, worst first?" --
 * over a different number: the gap to the analyst target, or the drop over a
 * time window. So the logic is written once here, and a page only says which
 * number it ranks by.
 */

/**
 * The sector filter as stored in the URL: the chosen sectors joined by commas
 * ("Technology,Healthcare"), and "" for all of them. No Yahoo sector name
 * contains a comma, so the comma is a safe separator.
 */
export function parseSectors(text: string): string[] {
  return text.split(",").filter((sector) => sector !== "");
}

export function joinSectors(sectors: string[]): string {
  return sectors.join(",");
}

/**
 * Keeps the rows of the chosen sectors (every sector when none is chosen)
 * whose number is at least `minimum` percent BELOW zero, and sorts them most
 * negative first.
 *
 * `minimum` is written as a positive number, the way the buttons read: 10
 * means "down 10% or more", i.e. the value is -10 or lower. `null` means no
 * minimum, and then rows with no number at all are kept too, at the end:
 * a missing number is not a reason to hide a company that did fire.
 *
 * `value` is a function rather than a column name so the caller can rank by
 * whichever field it likes, and TypeScript still checks it returns a number.
 */
export function rankCompanies<Row extends Company>(
  rows: Row[],
  value: (row: Row) => number | null,
  { sectors, minimum }: { sectors: string[]; minimum: number | null },
): Row[] {
  const kept = rows.filter((row) => {
    if (sectors.length > 0 && !sectors.includes(row.sector ?? "")) return false;
    if (minimum === null) return true;
    const v = value(row);
    return v !== null && v <= -minimum;
  });

  // `.sort` takes a function that says which of two rows goes first: a
  // negative result puts `a` first. Nulls are sent to the end. `[...kept]`
  // copies the array first, because `.sort` reorders in place.
  return [...kept].sort((a, b) => {
    const va = value(a);
    const vb = value(b);
    if (va === null) return vb === null ? 0 : 1;
    if (vb === null) return -1;
    return va - vb;
  });
}

/** Every sector present in `rows`, alphabetically, without repeats. */
export function sectorsOf(rows: Company[]): string[] {
  // A `Set` keeps one copy of each value, which is what removes the repeats.
  const sectors = new Set<string>();
  for (const row of rows) if (row.sector) sectors.add(row.sector);
  return [...sectors].sort();
}

/**
 * One filter value stored in the URL, e.g. `#/price-drops?window=var_1m`.
 *
 * WHY THE URL AND NOT `useState`. A value kept in component state is lost on
 * a reload and cannot be sent to someone else. In the URL it survives both,
 * and the browser's back button undoes a filter change for free.
 *
 * `useSearchParams` is React Router's hook for the `?a=1&b=2` part of the URL:
 * it returns the current values and a function to change them, and repaints
 * the page whenever they change, exactly like `useState`. `replace: true`
 * rewrites the current history entry instead of adding one, so each click on
 * a filter does not become one more step for the back button.
 *
 * An empty value removes the parameter, keeping the URL clean for defaults.
 */
export function useUrlParam(name: string, fallback: string): [string, (value: string) => void] {
  const [params, setParams] = useSearchParams();
  const value = params.get(name) ?? fallback;

  function setValue(next: string) {
    setParams(
      (previous) => {
        const updated = new URLSearchParams(previous);
        if (next === fallback) updated.delete(name);
        else updated.set(name, next);
        return updated;
      },
      { replace: true },
    );
  }

  return [value, setValue];
}

/**
 * The minimum-drop filter, as a number. Stored in the URL as text ("15"),
 * where "" means no minimum; anything that is not a positive number is read
 * as no minimum too, so a hand-edited URL cannot break the page.
 */
export function parseMinimum(text: string): number | null {
  const value = Number(text);
  return text === "" || !Number.isFinite(value) || value <= 0 ? null : value;
}
