import { AllCommunityModule, ModuleRegistry, themeQuartz, type ColDef } from "ag-grid-community";
import { AgGridReact } from "ag-grid-react";

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

// `ColDef` is AG Grid's type for a column definition. Re-exported here so that
// pages never import anything from ag-grid directly.
export type { ColDef };

// A COMPONENT'S PROPS are its inputs, like arguments to a function. `Row` is a
// generic: a placeholder for whatever row type each page uses (AnalystAlert,
// PriceAlert...). Thanks to it TypeScript rejects a `field` in `columns` that
// does not exist in `rows`. A `?` marks an optional prop.
type Props<Row> = {
  rows: Row[];
  columns: ColDef<Row>[];
  height?: number;
};

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
  return (
    <div style={{ height }}>
      <AgGridReact<Row>
        theme={themeQuartz}
        rowData={rows}
        columnDefs={columns}
        // Defaults applied to EVERY column. Each column can override them in
        // its own definition.
        defaultColDef={{
          flex: 1, // share the available width between columns
          minWidth: 110,
          sortable: true,
          filter: true,
          resizable: true,
        }}
      />
    </div>
  );
}
