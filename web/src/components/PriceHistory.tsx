import { useMemo, useState } from "react";
import { Chart, type ChartOption } from "./Chart";
import { formatNumber } from "../lib/format";
import type { PriceSeries } from "../lib/types";

/**
 * The price of one company over time, with a button per time range.
 *
 * The data arrives as a single series covering five years (daily for the last
 * year, weekly before that -- see `_price_rows` in json_export.py). Switching
 * range only decides how much of THAT array is drawn, so no new download
 * happens when the user presses a button.
 */

/** The ranges offered, and how many days back each one looks. */
const RANGES = [
  { label: "3M", days: 91 },
  { label: "1Y", days: 365 },
  { label: "5Y", days: 365 * 5 },
] as const;

/** The range a panel opens on. */
const DEFAULT_RANGE = "1Y";

/** Green when the range ends above where it started, red when below. */
const UP = "#15803d";
const DOWN = "#b91c1c";

/**
 * Keeps the points inside the range.
 *
 * The dates are `YYYY-MM-DD` strings, which compare correctly with `>=`
 * because that format sorts the same alphabetically as chronologically. That
 * saves turning thousands of strings into Date objects on every repaint.
 */
function withinRange(points: [string, number][], days: number): [string, number][] {
  if (points.length === 0) return points;

  const last = new Date(points[points.length - 1][0]);
  last.setDate(last.getDate() - days);
  const from = last.toISOString().slice(0, 10);

  return points.filter(([date]) => date >= from);
}

export function PriceHistory({ series }: { series: PriceSeries | null }) {
  // `useState` remembers which button is pressed. The type is the union of the
  // labels above ("3M" | "1Y" | "5Y"), so a typo is a compile error.
  const [range, setRange] = useState<(typeof RANGES)[number]["label"]>(DEFAULT_RANGE);

  // `useMemo` rebuilds the chart configuration only when the data or the range
  // changes. Without it a new object on every repaint would repaint the chart
  // forever (see the same note in AlertsPage).
  const option: ChartOption | null = useMemo(() => {
    if (!series || series.points.length === 0) return null;

    const days = RANGES.find((r) => r.label === range)?.days ?? 365;
    const points = withinRange(series.points, days);
    if (points.length === 0) return null;

    const rising = points[points.length - 1][1] >= points[0][1];
    const color = rising ? UP : DOWN;

    return {
      // Room for the axis labels, and no more: the panel is not a dashboard.
      grid: { left: 52, right: 12, top: 16, bottom: 28 },
      // `trigger: "axis"` shows the value of the day the pointer is nearest,
      // instead of requiring the pointer to land exactly on a point.
      tooltip: {
        trigger: "axis",
        formatter: (params) => {
          const [point] = Array.isArray(params) ? params : [params];
          const [date, close] = point.value as [string, number];
          return `${date}: ${formatNumber(close)}`;
        },
      },
      // `type: "time"` spaces the points by their real dates, so a gap in the
      // data (a weekend, a holiday) looks like a gap and not like a day.
      xAxis: { type: "time" },
      yAxis: {
        type: "value",
        // Prices rarely approach zero, and a line pinned to the top of the
        // chart hides its own shape. `scale` lets the axis start where the
        // data does.
        scale: true,
        axisLabel: { formatter: (value: number) => formatNumber(value) },
      },
      series: [
        {
          type: "line",
          data: points,
          showSymbol: false,
          lineStyle: { color, width: 1.6 },
          // A faint fill under the line, fading out downwards.
          areaStyle: { color, opacity: 0.08 },
        },
      ],
    };
  }, [series, range]);

  if (!option) {
    return <p className="muted">No price history available</p>;
  }

  return (
    <div>
      <div className="range-picker">
        {RANGES.map((choice) => (
          <button
            key={choice.label}
            type="button"
            className={choice.label === range ? "range active" : "range"}
            onClick={() => setRange(choice.label)}
          >
            {choice.label}
          </button>
        ))}
      </div>
      <Chart option={option} height={260} />
    </div>
  );
}
