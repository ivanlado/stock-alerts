import { useEffect, useRef } from "react";
import * as echarts from "echarts";

// `EChartsOption` is ECharts' configuration object: it describes axes, series,
// tooltip... Re-exported so that pages never import echarts directly.
export type ChartOption = echarts.EChartsOption;

type Props = {
  /**
   * Chart configuration. Wrap it in `useMemo` on the page so it is not rebuilt
   * on every repaint (see AlertsPage).
   */
  option: ChartOption;
  height?: number;
};

/**
 * Reusable chart. The only place in the project that knows about ECharts.
 *
 * Usage:  <Chart option={option} />
 *
 * WHY THIS IS MORE INVOLVED THAN DataGrid. ECharts is not a React library: it
 * paints into a DOM element by itself. So React must hand it an empty <div>
 * and stay out of the way. Two React tools make that possible:
 *
 *  - `useRef(initial)` is a box whose `.current` value survives repaints and,
 *    unlike state, changing it does NOT trigger one. Two uses here: getting
 *    hold of the real <div> (via the `ref` attribute), and storing the ECharts
 *    instance so later repaints can reuse it.
 *
 *  - `useEffect(fn, deps)` runs code outside React after painting. The `deps`
 *    array decides when it re-runs.
 *
 * The two effects are deliberately separate: the chart must be created only
 * once (empty `[]`), but repainted every time the data changes (`[option]`).
 */
export function Chart({ option, height = 320 }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);

  // Create the chart on mount, destroy it on unmount.
  useEffect(() => {
    if (!container.current) return;

    chart.current = echarts.init(container.current);

    // ECharts does not resize itself: we listen to the window and tell it to.
    const resize = () => chart.current?.resize();
    window.addEventListener("resize", resize);

    // Cleanup. Removing the listener and disposing the chart prevents a memory
    // leak every time the user leaves the page.
    return () => {
      window.removeEventListener("resize", resize);
      chart.current?.dispose();
      chart.current = null;
    };
  }, []); // empty array = run once only

  // Repaint whenever the data changes.
  // `chart.current?.setOption` is optional chaining: the `?.` skips the call
  // if `chart.current` is null instead of crashing.
  useEffect(() => {
    chart.current?.setOption(option, true);
  }, [option]);

  // The div React hands over to ECharts. `ref` fills in `container.current`.
  return <div ref={container} style={{ height, width: "100%" }} />;
}
