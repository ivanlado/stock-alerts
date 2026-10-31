import { useMemo, useState } from "react";
import { CompanyDetail } from "../components/CompanyCards";
import { DataGrid, type Column } from "../components/DataGrid";
import {
  ButtonPicker,
  FilterBar,
  MinimumPicker,
  RangePicker,
  SectorPicker,
} from "../components/Filters";
import { useData } from "../lib/data";
import {
  joinSectors,
  parseDecimal,
  parseMinimum,
  parseSectors,
  rankCompanies,
  sectorsOf,
  useUrlParam,
} from "../lib/filters";
import { formatNumber, formatPercent, variationStyle } from "../lib/format";
import {
  CURRENT_RATIO,
  DEBT_TO_EQUITY,
  FREE_CASH_FLOW,
  GAP,
  OPERATING_MARGIN,
  PER,
  PRICE_TO_SALES,
  REVENUE,
  REVENUE_GROWTH,
  formatMetric,
  type Metric,
} from "../lib/metrics";
import type { CompanyCard } from "../lib/types";
import { DEFAULT_WINDOW, PRICE_WINDOWS, windowLabel, type PriceWindowKey } from "../lib/windows";

/**
 * Search: every stock of the universe and every fund, screened or not, with
 * the filters set by hand.
 *
 * Unlike the alert pages, nothing is pre-filtered: "Any" means no filter at
 * all, so a company 5% below its target or one that rose this month is here
 * until a filter says otherwise.
 */

type AssetFilter = "" | "stock" | "fund";
const TYPE_OPTIONS: { value: AssetFilter; label: string }[] = [
  { value: "", label: "All" },
  { value: "stock", label: "Stocks" },
  { value: "fund", label: "Funds" },
];

const WINDOW_OPTIONS = PRICE_WINDOWS.map((w) => ({ value: w.key, label: w.label }));

const GAP_PRESETS = [5, 10, 20, 30];
const DROP_PRESETS = [5, 10, 15, 20];

/**
 * The fundamentals with a min/max filter. `param` is the prefix of their two
 * URL parameters (`pe_min`, `pe_max`). Adding one is a line here; its label,
 * unit and explanation come from lib/metrics.ts.
 */
const RANGE_FILTERS: { param: string; metric: Metric }[] = [
  { param: "pe", metric: PER },
  { param: "om", metric: OPERATING_MARGIN },
  { param: "de", metric: DEBT_TO_EQUITY },
  { param: "rg", metric: REVENUE_GROWTH },
];

/** The fundamental columns of the table, in order, after the price ones. */
const FUNDAMENTAL_COLUMNS: Metric[] = [
  PER,
  PRICE_TO_SALES,
  OPERATING_MARGIN,
  DEBT_TO_EQUITY,
  CURRENT_RATIO,
  REVENUE,
  REVENUE_GROWTH,
  FREE_CASH_FLOW,
];

/** A filter label with its unit, so the boxes need no "%" beside them. */
function rangeLabel(metric: Metric): string {
  return metric.unit === "percent" ? `${metric.label} (%)` : metric.label;
}

/**
 * Whether the metric's value falls inside [min, max]; an unset side does not
 * limit. A `positiveOnly` metric (PER) also rejects values at or below zero
 * once any bound is set: see Metric in lib/metrics.ts.
 */
function inRange(metric: Metric, value: number | null, min: number | null, max: number | null): boolean {
  if (min === null && max === null) return true;
  if (value === null) return false;
  if (metric.positiveOnly && value <= 0) return false;
  return (min === null || value >= min) && (max === null || value <= max);
}

/**
 * The two URL parameters of every range filter.
 *
 * Hooks must be called the same number of times on every repaint, in the same
 * order -- that is how React tells them apart. Calling `useUrlParam` inside a
 * loop over a FIXED array respects that rule: the array never changes length.
 */
function useRangeParams() {
  return RANGE_FILTERS.map(({ param, metric }) => {
    const [min, setMin] = useUrlParam(`${param}_min`, "");
    const [max, setMax] = useUrlParam(`${param}_max`, "");
    return { param, metric, min, max, setMin, setMax };
  });
}

/**
 * How wide a column must be for its whole header to show: the name, plus the
 * "i" and the sort and filter icons around it (~75px). About 8px a letter.
 */
function headerWidth(label: string, info: boolean): number {
  return Math.max(100, label.length * 8 + (info ? 95 : 75));
}

/** A coloured percentage column: price movement, on the shared green/red scale. */
function variationColumn(metric: Metric, info?: string): Column<CompanyCard> {
  return {
    headerName: metric.label,
    valueGetter: (params) => (params.data ? metric.value(params.data) : null),
    valueFormatter: (params) => formatPercent(params.value),
    cellStyle: (params) => variationStyle(params.value),
    numeric: true,
    info,
    minWidth: headerWidth(metric.label, Boolean(info)),
  };
}

/**
 * A fundamental column: neutral (a ratio has no up-is-good direction), with a
 * number filter and the metric's "i" in the header. Secondary on a phone,
 * where the price columns are what fits.
 */
function metricColumn(metric: Metric): Column<CompanyCard> {
  return {
    headerName: metric.label,
    valueGetter: (params) => (params.data ? metric.value(params.data) : null),
    valueFormatter: (params) => formatMetric(metric, params.value),
    numeric: true,
    info: metric.info,
    minWidth: headerWidth(metric.label, true),
    secondary: true,
  };
}

/** A plain price column (price, target), one decimal. */
function priceColumn(headerName: string, value: (c: CompanyCard) => number | null): Column<CompanyCard> {
  return {
    headerName,
    valueGetter: (params) => (params.data ? value(params.data) : null),
    valueFormatter: (params) => formatNumber(params.value),
    numeric: true,
    secondary: true,
  };
}

export function SearchPage() {
  const companies = useData<CompanyCard>("companies.json");
  const [selected, setSelected] = useState<CompanyCard | null>(null);

  const [typeText, setType] = useUrlParam("type", "");
  const assetType: AssetFilter = typeText === "stock" || typeText === "fund" ? typeText : "";
  const [sectorText, setSectorText] = useUrlParam("sector", "");
  const sectors = parseSectors(sectorText);
  const [gap, setGap] = useUrlParam("gap", "");
  const [windowText, setWindow] = useUrlParam("window", DEFAULT_WINDOW);
  const selectedWindow: PriceWindowKey = PRICE_WINDOWS.some((w) => w.key === windowText)
    ? (windowText as PriceWindowKey)
    : DEFAULT_WINDOW;
  const [drop, setDrop] = useUrlParam("drop", "");
  const ranges = useRangeParams();

  // The range bounds as numbers. When ANY is set, funds are left out: a fund
  // has no fundamentals, so it can never satisfy one.
  const bounds = ranges.map((r) => ({
    metric: r.metric,
    min: parseDecimal(r.min),
    max: parseDecimal(r.max),
  }));
  const anyBound = bounds.some((b) => b.min !== null || b.max !== null);

  const ofType = useMemo(
    () =>
      assetType === "" ? companies.rows : companies.rows.filter((c) => c.asset_type === assetType),
    [companies.rows, assetType],
  );

  // Every filter in one pass. Then `rankCompanies`, with no filter of its own,
  // only sorts: most undervalued against the target first.
  const gapMin = parseMinimum(gap);
  const dropMin = parseMinimum(drop);
  const shown = rankCompanies(
    ofType.filter((c) => {
      if (sectors.length > 0 && !sectors.includes(c.sector ?? "")) return false;
      if (gapMin !== null && !(c.pct_price_diff !== null && c.pct_price_diff <= -gapMin)) return false;
      const dropped = c[selectedWindow];
      if (dropMin !== null && !(dropped !== null && dropped <= -dropMin)) return false;
      if (anyBound && c.asset_type !== "stock") return false;
      return bounds.every((b) => inRange(b.metric, b.metric.value(c), b.min, b.max));
    }),
    (c) => c.pct_price_diff,
    { sectors: [], minimum: null },
  );

  // Rebuilt when the window changes, so its column follows the window buttons.
  const columns: Column<CompanyCard>[] = useMemo(() => {
    const windowMetric: Metric = {
      label: windowLabel(selectedWindow),
      unit: "percent",
      value: (c) => c[selectedWindow],
      info: "",
    };
    return [
      { field: "ticker", headerName: "Ticker", minWidth: 95, pinned: "left" },
      { field: "short_name", headerName: "Name", minWidth: 190 },
      { field: "sector", headerName: "Sector", minWidth: 150, secondary: true },
      priceColumn("Price", (c) => c.current),
      priceColumn("Target", (c) => c.median),
      variationColumn(GAP, GAP.info),
      variationColumn(windowMetric),
      ...FUNDAMENTAL_COLUMNS.map(metricColumn),
      {
        headerName: "Screened",
        valueGetter: (params) => (params.data?.screened ? "Yes" : "No"),
        minWidth: 110,
        secondary: true,
      },
    ];
  }, [selectedWindow]);

  if (companies.loading) return <p>Loading...</p>;
  if (companies.error) return <p className="error">{companies.error}</p>;

  return (
    <div>
      <h1>Search</h1>
      <p className="meta">
        Every stock and fund, screened or not. Click a row for the full profile.
        Generated at: {companies.generatedAt}
      </p>

      <FilterBar>
        <ButtonPicker label="Type" options={TYPE_OPTIONS} value={assetType} onChange={setType} />
        <SectorPicker
          sectors={sectorsOf(ofType)}
          value={sectors}
          onChange={(chosen) => setSectorText(joinSectors(chosen))}
        />
      </FilterBar>

      <FilterBar>
        <MinimumPicker
          label="Min. gap to analyst target"
          presets={GAP_PRESETS}
          value={gap}
          onChange={setGap}
        />
        <ButtonPicker
          label="Window"
          options={WINDOW_OPTIONS}
          value={selectedWindow}
          onChange={setWindow}
        />
        <MinimumPicker
          label={`Min. drop over ${windowLabel(selectedWindow)}`}
          presets={DROP_PRESETS}
          value={drop}
          onChange={setDrop}
        />
      </FilterBar>

      {/* A fund has no fundamentals, so with "Funds" chosen there is nothing
          to filter on here. Each box is one more filter of the same row,
          labelled like the ones above. */}
      {assetType !== "fund" && (
        <FilterBar>
          {ranges.map((r) => (
            <RangePicker
              key={r.param}
              label={rangeLabel(r.metric)}
              info={r.metric.info}
              min={r.min}
              max={r.max}
              onMin={r.setMin}
              onMax={r.setMax}
            />
          ))}
        </FilterBar>
      )}

      <p className="meta">
        Showing {shown.length} of {companies.rows.length}
        {assetType !== "fund" && " · Fundamental filters apply to stocks only"}
        {anyBound && assetType === "" && ", so funds are hidden while one is set"}
      </p>
      <DataGrid rows={shown} columns={columns} height={560} onRowClick={setSelected} />

      {selected && <CompanyDetail company={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
