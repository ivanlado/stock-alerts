import { useMemo } from "react";
import { Chart, type ChartOption } from "../components/Chart";
import { DataGrid, type ColDef } from "../components/DataGrid";
import { useData } from "../lib/data";
import type { AnalystAlert, PriceAlert } from "../lib/types";

// --- Column definitions ---
// Declared outside the component on purpose: they are constants, and a value
// defined inside would be rebuilt on every repaint for no reason.
// `field` must match the key in the JSON produced by Python; `headerName` is
// the label shown to the user.

const analystColumns: ColDef<AnalystAlert>[] = [
  { field: "ticker", headerName: "Ticker" },
  { field: "short_name", headerName: "Name" },
  { field: "current", headerName: "Price" },
  { field: "median", headerName: "Target" },
  { field: "pct_price_diff", headerName: "Diff %" },
];

const priceColumns: ColDef<PriceAlert>[] = [
  { field: "ticker", headerName: "Ticker" },
  { field: "short_name", headerName: "Name" },
  { field: "var_1m", headerName: "1M %" },
  { field: "var_3m", headerName: "3M %" },
  { field: "var_6m", headerName: "6M %" },
  { field: "var_9m", headerName: "9M %" },
];

/**
 * Alerts page: both alert rules, each in its own section.
 *
 * A PAGE IS JUST A FUNCTION returning what to display. React calls it again
 * every time the data changes, and repaints only what actually differs.
 */
export function AlertsPage() {
  const analyst = useData<AnalystAlert>("analyst_alerts.json");
  const price = useData<PriceAlert>("price_alerts.json");

  // `useMemo(fn, deps)` remembers the result of `fn` and only recomputes it
  // when a value in `deps` changes. Needed here because `Chart` repaints
  // whenever `option` is a different object: without useMemo a brand new
  // object would be built on every repaint, repainting the chart forever.
  const chartOption: ChartOption = useMemo(
    () => ({
      tooltip: {},
      // `.map()` turns an array into another array: here, rows into the list
      // of labels for the X axis and the list of values for the bars.
      xAxis: { type: "category", data: analyst.rows.map((r) => r.ticker) },
      yAxis: { type: "value", name: "Diff %" },
      series: [
        {
          type: "bar",
          data: analyst.rows.map((r) => r.pct_price_diff),
        },
      ],
    }),
    [analyst.rows],
  );

  // Early returns: while loading or on failure, display that instead of the
  // page. Reaching further down guarantees the data is there.
  if (analyst.loading || price.loading) return <p>Loading...</p>;
  if (analyst.error) return <p className="error">{analyst.error}</p>;
  if (price.error) return <p className="error">{price.error}</p>;

  // Curly braces inside JSX insert a JavaScript value into the markup.
  return (
    <div>
      <h1>Alerts</h1>
      <p className="meta">Generated at: {analyst.generatedAt}</p>

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
