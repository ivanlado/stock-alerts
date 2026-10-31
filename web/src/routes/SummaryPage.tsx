import { useMemo } from "react";
import { Link } from "react-router-dom";
import { CompanyCards, type CardBadge } from "../components/CompanyCards";
import { useData } from "../lib/data";
import { rankCompanies } from "../lib/filters";
import type { CompanyCard, PriceSeries } from "../lib/types";
import { DEFAULT_WINDOW, windowLabel } from "../lib/windows";

/** How many companies each section of the summary shows. */
const TOP = 5;

/** No sector, no minimum: the summary ranks every alert of each rule. */
const NO_FILTER = { sectors: [], minimum: null };

const ANALYST_BADGES: CardBadge[] = [
  { label: "vs target", value: (c) => c.pct_price_diff },
  { label: "1M", value: (c) => c.var_1m },
  { label: "3M", value: (c) => c.var_3m },
];

const PRICE_BADGES: CardBadge[] = [
  { label: windowLabel(DEFAULT_WINDOW), value: (c) => c[DEFAULT_WINDOW] },
  { label: "vs target", value: (c) => c.pct_price_diff },
];

/**
 * The home page: the strongest alerts of each rule, with a link to the full
 * list. It ranks exactly like the two alert pages do with their filters at
 * the defaults, so its top five are the first five there.
 */
export function SummaryPage() {
  const companies = useData<CompanyCard>("companies.json");
  const prices = useData<PriceSeries>("prices.json");

  // `.slice(0, TOP)` keeps the first TOP entries of the ranked list.
  const analyst = useMemo(
    () =>
      rankCompanies(
        companies.rows.filter((c) => c.analyst_alert),
        (c) => c.pct_price_diff,
        NO_FILTER,
      ),
    [companies.rows],
  );
  const drops = useMemo(
    () =>
      rankCompanies(
        companies.rows.filter((c) => c.price_alert),
        (c) => c[DEFAULT_WINDOW],
        NO_FILTER,
      ),
    [companies.rows],
  );

  if (companies.loading || prices.loading) return <p>Loading...</p>;
  if (companies.error) return <p className="error">{companies.error}</p>;
  if (prices.error) return <p className="error">{prices.error}</p>;

  return (
    <div>
      <h1>Summary</h1>
      <p className="meta">Generated at: {companies.generatedAt}</p>

      <section>
        <div className="section-head">
          <h2>Most undervalued vs analyst target</h2>
          {/* `Link` changes the page without reloading; see App.tsx. */}
          <Link to="/analyst">See all {analyst.length} →</Link>
        </div>
        {analyst.length === 0 && <p className="muted">No analyst alert today.</p>}
        <CompanyCards rows={analyst.slice(0, TOP)} prices={prices.rows} badges={ANALYST_BADGES} />
      </section>

      <section>
        <div className="section-head">
          <h2>Biggest price drops ({windowLabel(DEFAULT_WINDOW)})</h2>
          <Link to="/price-drops">See all {drops.length} →</Link>
        </div>
        {drops.length === 0 && <p className="muted">No price-drop alert today.</p>}
        <CompanyCards rows={drops.slice(0, TOP)} prices={prices.rows} badges={PRICE_BADGES} />
      </section>
    </div>
  );
}
