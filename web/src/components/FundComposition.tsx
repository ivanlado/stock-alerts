import { formatPercent } from "../lib/format";
import type { FundDetails } from "../lib/types";

/**
 * What a fund holds: its ten largest positions and its split by sector, each
 * drawn as a horizontal bar. The split by country is a single stacked bar of
 * its own (`CountryBar`, below), shown higher up in the panel.
 *
 * WHY BARS AND NOT A CHART. A list of names with a percentage beside them is
 * read top to bottom like a table; a bar behind each row adds the comparison
 * at a glance. That is a `<div>` whose CSS width is the weight, so no charting
 * library is needed.
 *
 * The bars are neutral grey-blue on purpose: green and red mean price
 * movement on this page, and a weight is not good or bad news.
 */

/**
 * One row: a label, its weight, and a bar `weight / max` of the full width.
 * Scaling to the largest row rather than to 100% keeps a 5% holding from
 * being a sliver nobody can compare with the next one.
 */
function WeightRow({
  label,
  detail,
  weight,
  max,
}: {
  label: string;
  detail?: string;
  weight: number;
  max: number;
}) {
  return (
    <li className="weight-row">
      <span className="weight-label">
        {label}
        {detail && <span className="meta"> {detail}</span>}
      </span>
      <span className="weight-value">{formatPercent(weight)}</span>
      {/* `style` takes a JavaScript object of CSS properties; this is the one
          value that depends on the data, so it is set here and not in CSS. */}
      <span className="weight-bar" style={{ width: `${(weight / max) * 100}%` }} />
    </li>
  );
}

export function FundComposition({ fund }: { fund: FundDetails | null }) {
  if (!fund) {
    return <p className="muted prose">No composition data for this fund today.</p>;
  }

  const holdings = fund.top_holdings;
  const sectors = fund.sectors;
  // `reduce` walks the array carrying a running value: here, the sum.
  const covered = holdings.reduce((sum, h) => sum + h.weight, 0);
  // `Math.max(...list)` spreads the array into arguments. The `1` guards
  // against an empty list, where the max would be -Infinity.
  const maxHolding = Math.max(1, ...holdings.map((h) => h.weight));
  const maxSector = Math.max(1, ...sectors.map((s) => s.weight));

  return (
    <>
      {fund.expense_ratio !== null && (
        <p className="meta">Annual fee (TER): {formatPercent(fund.expense_ratio)}</p>
      )}

      {holdings.length > 0 && (
        <>
          <h4>Top {holdings.length} holdings</h4>
          <p className="meta">
            Together {formatPercent(covered)} of the fund. The source publishes only the
            largest positions.
          </p>
          <ul className="weights">
            {holdings.map((h) => (
              <WeightRow
                key={h.symbol}
                label={h.name}
                detail={h.symbol}
                weight={h.weight}
                max={maxHolding}
              />
            ))}
          </ul>
        </>
      )}

      {sectors.length > 0 && (
        <>
          <h4>Sectors</h4>
          <ul className="weights">
            {sectors.map((s) => (
              <WeightRow key={s.sector} label={s.sector} weight={s.weight} max={maxSector} />
            ))}
          </ul>
        </>
      )}
    </>
  );
}

/**
 * Below this share a segment is too narrow for its text, which then lives only
 * in the hover tooltip. The bar spans the panel, so 8% is ~3rem or more.
 */
const MIN_LABELLED_WEIGHT = 8;

/**
 * The split by country as ONE bar: each country is a segment as wide as its
 * weight, labelled inside with its name and its weight rounded to a whole
 * number. "Other" is drawn grey, so it does not read as one more country.
 *
 * `flex-grow` does the proportions: each segment grows by its weight, so the
 * segments share the bar in exactly those ratios even when the weights do not
 * add up to 100 because of rounding at the source. `title` is the browser's
 * own hover tooltip, which keeps the narrow segments readable.
 */
export function CountryBar({ fund }: { fund: FundDetails | null }) {
  const countries = fund?.countries ?? [];
  if (countries.length === 0) return null;

  return (
    <>
      <h4>Countries</h4>
      <div className="country-bar">
        {countries.map((c, index) => {
          const text = `${c.country} ${Math.round(c.weight)}%`;
          const other = c.country === "Other";
          return (
            <div
              key={c.country}
              title={text}
              // Alternating two shades keeps neighbouring countries apart.
              className={other ? "country other" : index % 2 === 0 ? "country" : "country alt"}
              style={{ flexGrow: c.weight }}
            >
              {c.weight >= MIN_LABELLED_WEIGHT && text}
            </div>
          );
        })}
      </div>
      {fund?.countries_as_of && <p className="meta">As of {fund.countries_as_of}</p>}
    </>
  );
}
