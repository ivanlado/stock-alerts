import { AllCommunityModule, ModuleRegistry, themeQuartz, type ColDef } from "ag-grid-community";
import { AgGridReact } from "ag-grid-react";
import { useIsNarrow } from "../lib/useIsNarrow";

// --- Global AG Grid setup (runs once, when this file is first imported) ---
//
// AG Grid is split into "modules" and you must declare which ones you use.
// `AllCommunityModule` registers every free (MIT) feature: sorting, filtering,
// pagination, virtual scrolling, column resize/reorder, cell editing and CSV
// export.
//
// Paid features (pivot, row grouping, side panel, Excel export) are NOT
// available. If they are ever needed, install `ag-grid-enterprise` and swap
// this line for `AllEnterpriseModule`: this is the only file to touch.
ModuleRegistry.registerModules([AllCommunityModule]);

/**
 * A column definition: AG Grid's own `ColDef` plus one extra flag of ours.
 *
 * `secondary: true` marks a column worth showing on a laptop but not worth
 * the horizontal scrolling it would cost on a phone. This component drops
 * those columns on a narrow screen; pages only declare the intent.
 *
 * `&` is TypeScript's intersection: the new type has every field of `ColDef`
 * plus `secondary`. Re-exported so pages never import anything from ag-grid.
 */
export type Column<Row> = ColDef<Row> & { secondary?: boolean };
export type { ColDef };

// A COMPONENT'S PROPS are its inputs, like arguments to a function. `Row` is a
// generic: a placeholder for whatever row type each page uses (AnalystAlert,
// PriceAlert...). Thanks to it TypeScript rejects a `field` in `columns` that
// does not exist in `rows`. A `?` marks an optional prop.
type Props<Row> = {
  rows: Row[];
  columns: Column<Row>[];
  height?: number;
};

/** Height of the grid on a phone: a table taller than this eats the screen. */
const NARROW_HEIGHT = 280;

/** Minimum width per column. Tighter on a phone, to fit one more column. */
const NARROW_MIN_WIDTH = 90;
const WIDE_MIN_WIDTH = 110;

/**
 * The widest a single column may ask for on a phone. Without this cap the
 * company name (160px, comfortable on a laptop) would push everything else
 * off screen; below ~130px it truncates to "Abbott ..." and stops naming
 * anything, which is why the cap is not simply NARROW_MIN_WIDTH.
 */
const NARROW_MAX_WIDTH = 130;

/**
 * Reusable table. The only place in the project that knows about AG Grid.
 *
 * Usage:  <DataGrid rows={rows} columns={columns} />
 *
 * `{ rows, columns, height = 400 }` is destructuring: it pulls each prop into
 * its own variable, and gives `height` a default when the caller omits it.
 *
 * AG Grid requires its container to have a fixed CSS height -- hence the outer
 * <div>. Without it the table would render zero pixels tall.
 */
export function DataGrid<Row>({ rows, columns, height = 400 }: Props<Row>) {
  // `true` on a phone. The hook repaints this component when the width
  // crosses the breakpoint, so the columns below are recomputed.
  const isNarrow = useIsNarrow();

  // `.filter()` keeps only the elements for which the test is true: on a
  // narrow screen, the columns NOT marked as secondary. `.map()` then caps
  // the width each surviving column asked for, so a generous `minWidth`
  // written for a laptop does not push the rest of the table off screen.
  //
  // `{ ...column, minWidth }` is spreading: a copy of the column with that
  // one field replaced. The original array is a module-level constant and
  // must not be mutated.
  const visible = isNarrow
    ? columns
        .filter((column) => !column.secondary)
        .map((column) => ({
          ...column,
          minWidth: Math.min(column.minWidth ?? NARROW_MIN_WIDTH, NARROW_MAX_WIDTH),
        }))
    : columns;

  return (
    <div style={{ height: isNarrow ? Math.min(height, NARROW_HEIGHT) : height }}>
      <AgGridReact<Row>
        theme={themeQuartz}
        rowData={rows}
        columnDefs={visible}
        // Defaults applied to EVERY column. Each column can override them in
        // its own definition.
        defaultColDef={{
          flex: 1, // share the available width between columns
          minWidth: isNarrow ? NARROW_MIN_WIDTH : WIDE_MIN_WIDTH,
          sortable: true,
          filter: true,
          resizable: true,
        }}
      />
    </div>
  );
}
