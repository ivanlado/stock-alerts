import { useEffect, useState } from "react";
import {
  formatCompact,
  formatNumber,
  formatPercent,
  variationStyle,
  MISSING,
} from "../lib/format";
import type { CompanyCard, Fundamentals } from "../lib/types";

/**
 * The alerted companies as a grid of cards, each opening a full detail panel.
 *
 * WHY CARDS AND NOT A TABLE. These rows mix numbers with paragraphs of prose.
 * A table column tall enough to hold a paragraph is unreadable, so the numbers
 * get badges and the prose gets a clamped block that expands on click.
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
  key: Exclude<keyof Fundamentals, "year">;
  label: string;
  format: (value: number | null) => string;
};

const FUNDAMENTALS: FundamentalRow[] = [
  { key: "operating_margin", label: "Op. margin", format: formatPercent },
  { key: "debt_to_equity", label: "Debt/equity", format: formatNumber },
  { key: "current_ratio", label: "Current ratio", format: formatNumber },
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

/** The text shown for a company, best source first. */
function companyText(c: CompanyCard): string | null {
  // `??` is the nullish coalescing operator: it takes the left side unless it
  // is null or undefined, in which case it falls through to the right. The
  // LLM summary is preferred when it exists; Yahoo's description always does.
  return c.business ?? c.description ?? null;
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

/** The fundamentals of every reported year, one row per metric. */
function FundamentalsHistory({ history }: { history: Fundamentals[] }) {
  if (history.length === 0) return null;

  return (
    <div className="history-wrap">
      <table className="history">
        <thead>
          <tr>
            <th>Metric</th>
            {history.map((year) => (
              <th key={year.year}>{year.year}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {FUNDAMENTALS.map((row) => (
            <tr key={row.key}>
              <th scope="row">{row.label}</th>
              {history.map((year) => (
                <td key={year.year}>{row.format(year[row.key])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * The full detail panel, shown on top of the page when a card is clicked.
 *
 * `onClose` is a prop that happens to be a FUNCTION. Passing a function down
 * is how a child tells its parent something happened -- here, "the user wants
 * me gone" -- without the child needing to know what closing actually means.
 */
function Detail({ company, onClose }: { company: CompanyCard; onClose: () => void }) {
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

  const latest = company.fundamentals;

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
        {company.sector && <span className="sector">{company.sector}</span>}

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

        {/* Only rendered when the model actually answered: a quota or a
            timeout leaves this null, and an empty heading helps nobody. */}
        {company.explanation && (
          <>
            <h4>Why the price moved</h4>
            <p>{company.explanation}</p>
          </>
        )}

        {latest && (
          <>
            <h4>Fundamentals ({latest.year})</h4>
            <div className="stats">
              {FUNDAMENTALS.map((row) => (
                <Stat key={row.key} label={row.label} value={row.format(latest[row.key])} />
              ))}
            </div>
          </>
        )}

        {company.fundamentals_history.length > 1 && (
          <>
            <h4>By year</h4>
            <FundamentalsHistory history={company.fundamentals_history} />
          </>
        )}

        {company.business && (
          <>
            <h4>Business</h4>
            <p>{company.business}</p>
          </>
        )}
        {company.description && (
          <>
            <h4>Profile</h4>
            <p>{company.description}</p>
          </>
        )}
      </div>
    </div>
  );
}

export function CompanyCards({ rows }: { rows: CompanyCard[] }) {
  // `useState` is how a component remembers something across repaints. Here it
  // holds the company whose detail panel is open, or null when none is. React
  // repaints the moment the setter is called, which is what makes the panel
  // appear.
  const [selected, setSelected] = useState<CompanyCard | null>(null);

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
              {company.sector && <span className="sector">{company.sector}</span>}

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
      {selected && <Detail company={selected} onClose={() => setSelected(null)} />}
    </>
  );
}
