import { useMemo } from "react";
import { CompanyCards, type CardBadge } from "../components/CompanyCards";
import { FilterBar, MinimumPicker, Results, SectorPicker } from "../components/Filters";
import { useData } from "../lib/data";
import {
  joinSectors,
  parseMinimum,
  parseSectors,
  rankCompanies,
  sectorsOf,
  useUrlParam,
} from "../lib/filters";
import type { CompanyCard, PriceSeries } from "../lib/types";

/**
 * The minimum-gap buttons. "Any" (no minimum) comes first and already means
 * at least 10%: that is the rule's own threshold (`MAX_PCT_DIFF` in
 * `src/alerts/analysts_alert.py`), so only the companies past it are listed
 * and every button here is a stricter cut.
 */
const MINIMUM_PRESETS = [15, 20, 25, 30];

/** What the cards lead with: the gap the page is ranked by. */
const BADGES: CardBadge[] = [
  { label: "vs target", value: (c) => c.pct_price_diff },
  { label: "1M", value: (c) => c.var_1m },
  { label: "3M", value: (c) => c.var_3m },
];

/** The number this page ranks by: price against the analysts' median target. */
const gap = (c: CompanyCard) => c.pct_price_diff;

/**
 * Analyst alerts: the companies trading well below the analysts' target,
 * most undervalued first.
 *
 * A PAGE IS JUST A FUNCTION returning what to display. React calls it again
 * every time the data or a filter changes, and repaints only what differs.
 */
export function AnalystPage() {
  const companies = useData<CompanyCard>("companies.json");
  const prices = useData<PriceSeries>("prices.json");
  const [sectorText, setSectorText] = useUrlParam("sector", "");
  const sectors = parseSectors(sectorText);
  const [minimum, setMinimum] = useUrlParam("min", "");

  // `useMemo(fn, deps)` remembers the result of `fn` and only recomputes it
  // when a value in `deps` changes: the list is not re-filtered on repaints
  // that have nothing to do with it, such as opening a detail panel.
  const alerted = useMemo(() => companies.rows.filter((c) => c.analyst_alert), [companies.rows]);
  const shown = useMemo(
    () => rankCompanies(alerted, gap, { sectors, minimum: parseMinimum(minimum) }),
    [alerted, sectorText, minimum],
  );

  // Early returns: while loading or on failure, display that instead of the
  // page. Reaching further down guarantees the data is there.
  if (companies.loading || prices.loading) return <p>Loading...</p>;
  if (companies.error) return <p className="error">{companies.error}</p>;
  if (prices.error) return <p className="error">{prices.error}</p>;

  return (
    <div>
      <h1>Analyst alerts</h1>
      <p className="meta">
        Companies trading at least 10% below the analysts' median price target, most
        undervalued first. Generated at: {companies.generatedAt}
      </p>

      <FilterBar>
        <SectorPicker
          sectors={sectorsOf(alerted)}
          value={sectors}
          onChange={(chosen) => setSectorText(joinSectors(chosen))}
        />
        <MinimumPicker
          label="Min. gap to target"
          presets={MINIMUM_PRESETS}
          value={minimum}
          onChange={setMinimum}
        />
      </FilterBar>

      <Results count={shown.length} total={alerted.length} />
      <CompanyCards rows={shown} prices={prices.rows} badges={BADGES} />
    </div>
  );
}
