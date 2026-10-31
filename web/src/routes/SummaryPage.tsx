import { useMemo } from "react";
import { Link } from "react-router-dom";
import { CompanyCards, type CardBadge } from "../components/CompanyCards";
import { useData } from "../lib/data";
import { rankCompanies } from "../lib/filters";
import type { CompanyCard, PriceSeries } from "../lib/types";
import { windowLabel, type PriceWindowKey } from "../lib/windows";

/** How many companies each section of the summary shows. */
const TOP = 5;

/** No sector, no minimum: the summary ranks every alert of each rule. */
const NO_FILTER = { sectors: [], minimum: null };

const ANALYST_BADGES: CardBadge[] = [
  { label: "vs target", value: (c) => c.pct_price_diff },
  { label: "1M", value: (c) => c.var_1m },
  { label: "3M", value: (c) => c.var_3m },
];

/**
 * The price-drop windows the summary shows, in order: what happened today,
 * this week, and over half a year.
 */
const DROP_WINDOWS: PriceWindowKey[] = ["var_1d", "var_1w", "var_6m"];

/**
 * One section: a heading, a "See all" link and the first TOP cards. The
 * analyst section and the three price ones are the same markup.
 */
function SummarySection({
  title,
  link,
  rows,
  empty,
  badges,
  prices,
}: {
  title: string;
  link: string;
  rows: CompanyCard[];
  empty: string;
  badges: CardBadge[];
  prices: PriceSeries[];
}) {
  return (
    <section>
      <div className="section-head">
        <h2>{title}</h2>
        {/* `Link` changes the page without reloading; see App.tsx. */}
        {rows.length > 0 && <Link to={link}>See all {rows.length} →</Link>}
      </div>
      {rows.length === 0 && <p className="muted">{empty}</p>}
      <CompanyCards rows={rows.slice(0, TOP)} prices={prices} badges={badges} compact />
    </section>
  );
}

/**
 * The home page: the strongest alerts of each rule, with a link to the full
 * list. It ranks exactly like the two alert pages do, so each section's top
 * five are the first five there with the same window chosen.
 *
 * A price section lists the companies and funds that fired the price rule
 * AND fell over that window: one that fired over 6M but rose today has no
 * place under "1D".
 */
export function SummaryPage() {
  const companies = useData<CompanyCard>("companies.json");
  const prices = useData<PriceSeries>("prices.json");

  // `useMemo` recomputes only when the downloaded rows change.
  const analyst = useMemo(
    () =>
      rankCompanies(
        companies.rows.filter((c) => c.analyst_alert),
        (c) => c.pct_price_diff,
        NO_FILTER,
      ),
    [companies.rows],
  );
  // One ranked list per window. `Object.fromEntries` turns a list of
  // [key, value] pairs into an object: { var_1d: [...], var_1w: [...], ... }.
  const drops = useMemo(() => {
    const fired = companies.rows.filter((c) => c.price_alert);
    return Object.fromEntries(
      DROP_WINDOWS.map((w) => [
        w,
        rankCompanies(
          fired.filter((c) => (c[w] ?? 0) < 0),
          (c) => c[w],
          NO_FILTER,
        ),
      ]),
    ) as Record<PriceWindowKey, CompanyCard[]>;
  }, [companies.rows]);

  if (companies.loading || prices.loading) return <p>Loading...</p>;
  if (companies.error) return <p className="error">{companies.error}</p>;
  if (prices.error) return <p className="error">{prices.error}</p>;

  return (
    <div className="summary">
      <h1>Summary</h1>
      <p className="meta">Generated at: {companies.generatedAt}</p>

      <SummarySection
        title="Most undervalued vs analyst target"
        link="/analyst"
        rows={analyst}
        empty="No analyst alert today."
        badges={ANALYST_BADGES}
        prices={prices.rows}
      />

      {DROP_WINDOWS.map((w) => (
        <SummarySection
          key={w}
          title={`Biggest price drops (${windowLabel(w)})`}
          link={`/price-drops?window=${w}`}
          rows={drops[w]}
          empty={`No price-drop alert fell over ${windowLabel(w)}.`}
          badges={[
            { label: windowLabel(w), value: (c) => c[w] },
            { label: "vs target", value: (c) => c.pct_price_diff },
          ]}
          prices={prices.rows}
        />
      ))}
    </div>
  );
}
