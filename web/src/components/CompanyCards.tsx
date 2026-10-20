import { useEffect, useMemo, useState } from "react";
import { PriceHistory } from "./PriceHistory";
import {
  formatCompact,
  formatNumber,
  formatPercent,
  variationStyle,
  MISSING,
} from "../lib/format";
import type { CompanyCard, CompanyProfile, Fundamentals, PriceSeries } from "../lib/types";

/**
 * The screened companies as a grid of cards, each opening a full detail panel.
 *
 * WHY CARDS AND NOT A TABLE. These rows mix numbers with paragraphs of prose.
 * A table column tall enough to hold a paragraph is unreadable, so the numbers
 * get badges and the prose gets a clamped block that expands on click.
 *
 * THE PROSE IS IN SPANISH. It is written by the model (see `src/enrichment/`)
 * and is the only text on the page this code does not produce. The headings
 * around it stay English, like every other label in the project.
 */

/**
 * Every fundamental the web shows, in the order it is shown, each with how to
 * write it.
 *
 * Declared once here so the card, the detail list and the year-by-year table
 * cannot disagree about a label or a unit. `key` is restricted to the keys of
 * Fundamentals, so a typo is a compile error rather than an empty cell.
 */
type FundamentalRow = {
  key: Exclude<keyof Fundamentals, "period">;
  label: string;
  format: (value: number | null) => string;
};

const FUNDAMENTALS: FundamentalRow[] = [
  { key: "operating_margin", label: "Op. margin", format: formatPercent },
  { key: "debt_to_equity", label: "Debt/equity", format: formatNumber },
  { key: "current_ratio", label: "Current ratio", format: formatNumber },
  { key: "price_earnings", label: "PER", format: formatNumber },
  { key: "price_to_sales", label: "Price/sales", format: formatNumber },
  { key: "total_revenue", label: "Revenue", format: formatCompact },
  { key: "cost_of_revenue", label: "Cost of revenue", format: formatCompact },
  { key: "ebitda", label: "EBITDA", format: formatCompact },
  { key: "free_cash_flow", label: "Free cash flow", format: formatCompact },
];

/**
 * The three the cards lead with: the very ratios the Python screener filters
 * on, so a card shows why the company got through in the first place.
 */
const HEADLINE_FUNDAMENTALS = FUNDAMENTALS.slice(0, 3);

/**
 * The two price-based ratios AS OF TODAY, read straight off the company row
 * rather than out of a reported period.
 *
 * They are kept apart from `FUNDAMENTALS` on purpose. Everything in that array
 * belongs to a year the company reported; these two are today's price over the
 * last twelve months' earnings and sales, so they have no period and cannot go
 * in the same table. The year-by-year version of the same two ratios IS in
 * that array (`price_earnings`, `price_to_sales`), measured at each year's
 * closing price, which is what the History table shows.
 */
const VALUATION: { key: "trailing_pe" | "price_to_sales"; label: string }[] = [
  { key: "trailing_pe", label: "PER" },
  { key: "price_to_sales", label: "Price/sales" },
];

/**
 * The profile sections shown in the detail panel, in order.
 *
 * `key` must match a key of `CompanyProfile`, which is what Python writes from
 * `PROFILE_SECTIONS` in `src/enrichment/prompts.py`. Adding a question there
 * and a line here is the whole job; `summary` is missing on purpose, since it
 * is shown at the top rather than as one section among others.
 */
const PROFILE_SECTIONS: { key: keyof CompanyProfile; heading: string }[] = [
  { key: "revenue_sources", heading: "Revenue sources" },
  { key: "moat", heading: "Economic moat" },
  { key: "competitors", heading: "Competitors" },
  { key: "threats", heading: "Threats" },
  { key: "outlook", heading: "Outlook" },
];

/** The short text shown on a card, best source first. */
function companyText(c: CompanyCard): string | null {
  // `?.` skips the lookup when `profile` is null instead of crashing, and `??`
  // takes the left side unless it is null or undefined. So: the model's own
  // two-line summary when it exists, and Yahoo's description -- which is there
  // for every ticker but far longer -- only as a fallback.
  return c.profile?.summary ?? c.description ?? null;
}

/** One coloured number: green for a rise, red for a drop. */
function Metric({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="metric" style={variationStyle(value)}>
      <span className="metric-label">{label}</span>
      <span className="metric-value">{formatPercent(value)}</span>
    </div>
  );
}

/**
 * One fundamental, deliberately NOT colour-coded.
 *
 * Green and red mean "the price went up / down" everywhere else on this page.
 * A debt ratio has no such direction -- low is good, which would invert the
 * meaning -- so painting it on the same scale would mislead. It stays neutral.
 */
function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat">
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
    </div>
  );
}

/**
 * Which rules fired, as small pills.
 *
 * Every card now carries BOTH rules' numbers, so the numbers alone no longer
 * say what made the company show up. These do.
 */
function AlertTags({ company }: { company: CompanyCard }) {
  return (
    <span className="tags">
      {company.analyst_alert && <span className="tag">Analyst target</span>}
      {company.price_alert && <span className="tag">Price drop</span>}
    </span>
  );
}

/**
 * One prose section, rendered only when the model actually answered.
 *
 * Heading and paragraph share a `.prose` wrapper so they move together: the
 * text is capped at a readable line length and centred in the panel, which
 * is wider than prose wants to be (see `.prose` in index.css).
 */
function Section({ heading, text }: { heading: string; text: string | null | undefined }) {
  if (!text) return null;
  return (
    <div className="prose">
      <h4>{heading}</h4>
      <p>{text}</p>
    </div>
  );
}

/**
 * The fundamentals of every reported period, one row per metric.
 *
 * The same component draws the annual and the quarterly table: Python gives
 * both the same shape, with `period` holding "2025" or "2025Q3".
 */
function FundamentalsHistory({ history }: { history: Fundamentals[] }) {
  if (history.length === 0) return null;

  // A metric with no value in ANY period gets no row: a line of dashes reads
  // like broken data. This is how PER and price/sales disappear from the
  // quarterly table, where they are deliberately not computed -- a quarter's
  // earnings would put the PER at four times its real value.
  const rows = FUNDAMENTALS.filter((row) =>
    history.some((entry) => entry[row.key] !== null && entry[row.key] !== undefined),
  );

  return (
    <div className="history-wrap">
      <table className="history">
        <thead>
          <tr>
            <th>Metric</th>
            {history.map((entry) => (
              <th key={entry.period}>{entry.period}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key}>
              <th scope="row">{row.label}</th>
              {history.map((entry) => (
                <td key={entry.period}>{row.format(entry[row.key])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * The year-by-year table and the quarter-by-quarter one, behind two buttons.
 *
 * Both are already downloaded, so switching only changes which array is drawn.
 * The quarterly view is offered only when Yahoo publishes one: not every
 * market requires quarterly statements, and an empty table says nothing.
 */
function FundamentalsTables({
  annual,
  quarterly,
}: {
  annual: Fundamentals[];
  quarterly: Fundamentals[];
}) {
  const [view, setView] = useState<"annual" | "quarterly">("annual");

  // Nothing worth a table: a single year is already shown as badges above.
  if (annual.length <= 1 && quarterly.length === 0) return null;

  const showing = view === "quarterly" && quarterly.length > 0 ? quarterly : annual;

  return (
    <>
      <h4>History</h4>
      {quarterly.length > 0 && (
        <div className="range-picker">
          <button
            type="button"
            className={view === "annual" ? "range active" : "range"}
            onClick={() => setView("annual")}
          >
            Annual
          </button>
          <button
            type="button"
            className={view === "quarterly" ? "range active" : "range"}
            onClick={() => setView("quarterly")}
          >
            Quarterly
          </button>
        </div>
      )}
      <FundamentalsHistory history={showing} />
    </>
  );
}

/**
 * The full detail panel, shown on top of the page when a card is clicked.
 *
 * `onClose` is a prop that happens to be a FUNCTION. Passing a function down
 * is how a child tells its parent something happened -- here, "the user wants
 * me gone" -- without the child needing to know what closing actually means.
 */
function Detail({
  company,
  series,
  onClose,
}: {
  company: CompanyCard;
  series: PriceSeries | null;
  onClose: () => void;
}) {
  // Closing with the Escape key is a browser-wide concern, not something that
  // happens inside this markup, so it needs useEffect: React runs the code
  // after painting, and runs the returned cleanup before the panel disappears.
  // Without that cleanup the listener would pile up on every open.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  // Freezing the page behind the panel, for the same reason and in the same
  // way: the panel scrolls on its own, and without this the wheel would keep
  // scrolling the list of cards underneath once the panel reached its end.
  // The cleanup restores whatever the page had before, rather than assuming
  // it was the default.
  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, []);

  const latest = company.fundamentals;
  const profile = company.profile;
  const summary = companyText(company);

  return (
    // Clicking the dark backdrop closes the panel. `stopPropagation` on the
    // inner box prevents a click INSIDE the panel from bubbling up to the
    // backdrop and closing it immediately.
    <div className="detail-backdrop" onClick={onClose}>
      <div className="detail" onClick={(event) => event.stopPropagation()}>
        <button className="detail-close" onClick={onClose} aria-label="Close">
          ×
        </button>

        <h3>
          {company.ticker} <span className="meta">{company.short_name}</span>
        </h3>
        <div className="detail-tags">
          {company.sector && <span className="sector">{company.sector}</span>}
          <AlertTags company={company} />
        </div>

        <div className="detail-numbers">
          <p>
            Price {formatNumber(company.current)} · Target {formatNumber(company.median)}
          </p>
          <div className="metrics">
            <Metric label="vs target" value={company.pct_price_diff} />
            <Metric label="1M" value={company.var_1m} />
            <Metric label="3M" value={company.var_3m} />
            <Metric label="6M" value={company.var_6m} />
            <Metric label="9M" value={company.var_9m} />
          </div>
        </div>

        {/* Its own heading, away from the reported figures below: these are
            today's price over the last twelve months, not the 2025 accounts,
            and filing them under "Fundamentals (2025)" would date them wrong. */}
        <h4>Valuation (today)</h4>
        <div className="stats">
          {VALUATION.map((row) => (
            <Stat key={row.key} label={row.label} value={formatNumber(company[row.key])} />
          ))}
        </div>

        {latest && (
          <>
            <h4>Fundamentals ({latest.period})</h4>
            <div className="stats">
              {FUNDAMENTALS.map((row) => (
                <Stat key={row.key} label={row.label} value={row.format(latest[row.key])} />
              ))}
            </div>
          </>
        )}

        <h4>Price history</h4>
        <PriceHistory series={series} />

        <Section heading="Summary" text={summary} />

        {/* Written on every run, unlike the sections below: it is about
            today's move, so a cached answer would be a wrong one. Null when
            the model call failed (a quota, a timeout). */}
        <Section heading="Recent move" text={company.explanation} />

        {PROFILE_SECTIONS.map((section) => (
          <Section
            key={section.key}
            heading={section.heading}
            text={profile ? profile[section.key] : null}
          />
        ))}

        {/* An absent profile is a normal state -- the model may have been out
            of quota when this company came up -- and an unexplained gap where
            six sections should be reads as a broken page. So it says so. */}
        {!profile && (
          <p className="muted prose">
            No profile written yet: the model had nothing to say about this company on
            the last run. It is filled in on a later run and then cached.
          </p>
        )}

        {/* `?? []` guards against data written by an older Python: a
            dashboard whose JSON predates a new column should show less, not
            crash. The files are regenerated daily, but a checkout is not. */}
        <FundamentalsTables
          annual={company.fundamentals_history ?? []}
          quarterly={company.fundamentals_quarterly ?? []}
        />
      </div>
    </div>
  );
}

export function CompanyCards({
  rows,
  prices = [],
}: {
  rows: CompanyCard[];
  prices?: PriceSeries[];
}) {
  // `useState` is how a component remembers something across repaints. Here it
  // holds the company whose detail panel is open, or null when none is. React
  // repaints the moment the setter is called, which is what makes the panel
  // appear.
  const [selected, setSelected] = useState<CompanyCard | null>(null);

  // A Map is a lookup table: finding a ticker in it is immediate, whereas
  // searching the array again on every repaint would walk it from the start.
  // `useMemo` builds it only when the downloaded prices change.
  const seriesByTicker = useMemo(
    () => new Map(prices.map((series) => [series.ticker, series])),
    [prices],
  );

  if (rows.length === 0) return null;

  return (
    <>
      <div className="cards">
        {/* `key` lets React tell list items apart between repaints, so it
            reuses the right element instead of rebuilding the whole list. */}
        {rows.map((company) => {
          const text = companyText(company);
          const latest = company.fundamentals;
          return (
            <article
              key={company.ticker}
              className="card"
              onClick={() => setSelected(company)}
            >
              <h3>
                {company.ticker} <span className="meta">{company.short_name}</span>
              </h3>
              <div className="detail-tags">
                {company.sector && <span className="sector">{company.sector}</span>}
                <AlertTags company={company} />
              </div>

              <div className="metrics">
                <Metric label="vs target" value={company.pct_price_diff} />
                <Metric label="1M" value={company.var_1m} />
                <Metric label="6M" value={company.var_6m} />
              </div>

              <div className="stats">
                {HEADLINE_FUNDAMENTALS.map((row) => (
                  <Stat
                    key={row.key}
                    label={row.label}
                    value={latest ? row.format(latest[row.key]) : MISSING}
                  />
                ))}
                {VALUATION.map((row) => (
                  <Stat key={row.key} label={row.label} value={formatNumber(company[row.key])} />
                ))}
              </div>

              {/* The text is clamped to a few lines by CSS rather than cut in
                  JavaScript, so the full string stays in the DOM and the panel
                  has it ready. */}
              <p className="card-text">
                {text ?? <span className="muted">No description available</span>}
              </p>
              <span className="card-more">Read more</span>
            </article>
          );
        })}
      </div>

      {/* Rendered only while something is selected. */}
      {selected && (
        <Detail
          company={selected}
          series={seriesByTicker.get(selected.ticker) ?? null}
          onClose={() => setSelected(null)}
        />
      )}
    </>
  );
}
