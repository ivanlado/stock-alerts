import { useMemo } from "react";
import { Chart, type ChartOption } from "../components/Chart";
import { CompanyCards } from "../components/CompanyCards";
import { DataGrid, type ColDef, type Column } from "../components/DataGrid";
import { useData } from "../lib/data";
import { formatNumber, formatPercent, variationStyle } from "../lib/format";
import type {
  AnalystAlert,
  Company,
  CompanyCard,
  PriceAlert,
  PriceSeries,
} from "../lib/types";

// --- Shared column behaviour ---
// Declared outside the component on purpose: they are constants, and a value
// defined inside would be rebuilt on every repaint for no reason.

/** How long a hover tooltip may get before it is cut short. */
const TOOLTIP_LIMIT = 400;

/**
 * A column of percentages: rounded to one decimal and shaded green or red.
 *
 * `valueFormatter` changes only what is DISPLAYED -- the underlying number is
 * what AG Grid keeps sorting and filtering by, so the order stays correct.
 * `cellStyle` returns the CSS for that one cell, so each value is shaded by
 * its own magnitude.
 */
function percentColumn<Row>(
  field: ColDef<Row>["field"],
  headerName: string,
  secondary = false,
): Column<Row> {
  return {
    field,
    headerName,
    secondary,
    valueFormatter: (params) => formatPercent(params.value),
    cellStyle: (params) => variationStyle(params.value),
  };
}

/**
 * A column of plain prices, rounded to one decimal. Marked `secondary`: on a
 * phone the difference between price and target says it all, and the two
 * absolute numbers are one tap away on the company card.
 */
function priceColumn<Row>(field: ColDef<Row>["field"], headerName: string): Column<Row> {
  return {
    field,
    headerName,
    secondary: true,
    valueFormatter: (params) => formatNumber(params.value),
  };
}

/**
 * The company name, with its profile shown on hover.
 *
 * `tooltipValueGetter` returns the text AG Grid shows when the pointer rests
 * on the cell. Yahoo's description is what the alert tables carry, and it is
 * there for every ticker; the model's shorter summary lives on the company
 * cards, which is where the full profile is.
 */
function nameColumn<Row extends Company>(field: ColDef<Row>["field"]): Column<Row> {
  return {
    field,
    headerName: "Name",
    minWidth: 160,
    tooltipValueGetter: (params) => {
      const text = params.data?.description;
      if (!text) return "No description available";
      return text.length > TOOLTIP_LIMIT ? `${text.slice(0, TOOLTIP_LIMIT)}…` : text;
    },
  };
}

// `secondary: true` = dropped on a phone by DataGrid, so the columns that
// remain fit without sideways scrolling. The sector goes first: it is a pill
// on every company card already.
const analystColumns: Column<AnalystAlert>[] = [
  { field: "ticker", headerName: "Ticker", minWidth: 100 },
  nameColumn<AnalystAlert>("short_name"),
  { field: "sector", headerName: "Sector", minWidth: 140, secondary: true },
  priceColumn<AnalystAlert>("current", "Price"),
  priceColumn<AnalystAlert>("median", "Target"),
  percentColumn<AnalystAlert>("pct_price_diff", "Diff %"),
];

const priceColumns: Column<PriceAlert>[] = [
  { field: "ticker", headerName: "Ticker", minWidth: 100 },
  nameColumn<PriceAlert>("short_name"),
  { field: "sector", headerName: "Sector", minWidth: 140, secondary: true },
  percentColumn<PriceAlert>("var_1m", "1M %"),
  percentColumn<PriceAlert>("var_3m", "3M %"),
  percentColumn<PriceAlert>("var_6m", "6M %"),
  // The longest window is the one to drop on a phone: the shorter ones are
  // what the alert reacts to first.
  percentColumn<PriceAlert>("var_9m", "9M %", true),
];

/**
 * Alerts page: both alert rules, each in its own section, plus one card per
 * alerted company.
 *
 * A PAGE IS JUST A FUNCTION returning what to display. React calls it again
 * every time the data changes, and repaints only what actually differs.
 */
export function AlertsPage() {
  const analyst = useData<AnalystAlert>("analyst_alerts.json");
  const price = useData<PriceAlert>("price_alerts.json");
  const companies = useData<CompanyCard>("companies.json");
  const prices = useData<PriceSeries>("prices.json");

  // `useMemo(fn, deps)` remembers the result of `fn` and only recomputes it
  // when a value in `deps` changes. Needed here because `Chart` repaints
  // whenever `option` is a different object: without useMemo a brand new
  // object would be built on every repaint, repainting the chart forever.
  const chartOption: ChartOption = useMemo(
    () => ({
      tooltip: {
        // ECharts hands the formatter either one hovered point or an array of
        // them. Only the first matters here, since the chart has one series.
        formatter: (params) => {
          const [point] = Array.isArray(params) ? params : [params];
          return `${point.name}: ${formatPercent(point.value as number | null)}`;
        },
      },
      // `.map()` turns an array into another array: here, rows into the list
      // of labels for the X axis and the list of values for the bars.
      xAxis: { type: "category", data: analyst.rows.map((r) => r.ticker) },
      yAxis: {
        type: "value",
        name: "Diff %",
        axisLabel: { formatter: "{value}%" },
      },
      series: [
        {
          type: "bar",
          // Each bar carries its own colour, on the same fixed scale the
          // tables use. A bar is given as `{ value, itemStyle }` rather than
          // as a bare number so the colour travels with the value.
          data: analyst.rows.map((r) => ({
            value: r.pct_price_diff,
            itemStyle: { color: variationStyle(r.pct_price_diff).backgroundColor },
          })),
        },
      ],
    }),
    [analyst.rows],
  );

  // Early returns: while loading or on failure, display that instead of the
  // page. Reaching further down guarantees the data is there.
  if (analyst.loading || price.loading || companies.loading || prices.loading)
    return <p>Loading...</p>;
  if (analyst.error) return <p className="error">{analyst.error}</p>;
  if (price.error) return <p className="error">{price.error}</p>;
  if (companies.error) return <p className="error">{companies.error}</p>;
  if (prices.error) return <p className="error">{prices.error}</p>;

  // Curly braces inside JSX insert a JavaScript value into the markup.
  return (
    <div>
      <h1>Alerts</h1>
      <p className="meta">Generated at: {analyst.generatedAt}</p>

      <section>
        <h2>Companies</h2>
        <p className="meta">
          Every company that passed the fundamental screener, with both rules'
          numbers. The ones that fired an alert come first. Click a card for the
          full profile.
        </p>
        <CompanyCards rows={companies.rows} prices={prices.rows} />
      </section>

      <section>
        <h2>Price vs analyst target</h2>
        <Chart option={chartOption} />
        <DataGrid rows={analyst.rows} columns={analystColumns} />
      </section>

      <section>
        <h2>Price drops</h2>
        <DataGrid rows={price.rows} columns={priceColumns} />
      </section>
    </div>
  );
}
