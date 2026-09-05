import { useEffect, useState } from "react";
import type { Payload } from "./types";

/**
 * The only place that knows where the data comes from.
 * Today these are static files in `public/data/` written by the Python
 * pipeline. If there is ever an API, only this constant and the fetch change.
 */
const DATA_URL = "data";

/**
 * Downloads one JSON file.
 *
 * `async`/`await`: downloading takes time, so the browser must not freeze
 * while it happens. An `async` function returns a Promise -- a value that is
 * not ready yet -- and `await` pauses only this function until it arrives.
 * `Promise<Payload<Row>>` as the return type means "a Payload, eventually".
 */
async function fetchPayload<Row>(file: string): Promise<Payload<Row>> {
  const response = await fetch(`${DATA_URL}/${file}`);
  if (!response.ok) {
    throw new Error(`Could not load ${file} (HTTP ${response.status})`);
  }
  return response.json();
}

/** What the hook returns: while `loading` is true, ignore `rows` and `error`. */
type Result<Row> = {
  rows: Row[];
  generatedAt: string | null;
  loading: boolean;
  error: string | null;
};

/**
 * Loads a data file and exposes its state. Exists so that pages do not repeat
 * the same loading logic.
 *
 * Usage:  const { rows, loading, error } = useData<AnalystAlert>("analyst_alerts.json");
 *
 * WHAT A HOOK IS. A function whose name starts with `use` and that lets a
 * component remember things across repaints. Two React hooks are used here:
 *
 *  - `useState(initial)` declares a value React remembers, and a function to
 *    change it. Assigning to a normal variable would be lost on the next
 *    repaint; calling the setter tells React to repaint with the new value.
 *
 *  - `useEffect(fn, deps)` runs code that reaches outside React -- here, a
 *    network request. React runs `fn` after painting, and again whenever a
 *    value in the `deps` array changes. Returning a function from `fn` gives
 *    React a cleanup step to run before the next execution or when the
 *    component disappears from the screen.
 *
 * The `cancelled` flag below is the standard guard against a race condition:
 * if the user navigates away before the download finishes, updating state on a
 * component that is gone is a bug, so the cleanup flips the flag first.
 */
export function useData<Row>(file: string): Result<Row> {
  const [rows, setRows] = useState<Row[]>([]);
  const [generatedAt, setGeneratedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setError(null);

    // `.then` runs on success, `.catch` on failure, `.finally` always.
    fetchPayload<Row>(file)
      .then((payload) => {
        if (cancelled) return; // the component is no longer on screen
        setRows(payload.rows);
        setGeneratedAt(payload.generated_at);
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    // Cleanup: runs before the next execution or on unmount.
    return () => {
      cancelled = true;
    };
  }, [file]); // re-run only when the requested file changes

  return { rows, generatedAt, loading, error };
}
