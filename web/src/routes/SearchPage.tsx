import { DataGrid, type ColDef } from "../components/DataGrid";
import { useData } from "../lib/data";
import type { ScreenerRow } from "../lib/types";

// PLACEHOLDER: for now this only lists the tickers that pass the fundamental
// screener. Once the search feature is defined, its filters and the
// fundamentals columns go here (they must be exported from Python first).
const columns: ColDef<ScreenerRow>[] = [
  { field: "ticker", headerName: "Ticker" },
  { field: "short_name", headerName: "Name" },
];

export function SearchPage() {
  // Destructuring the hook result straight into variables, since this page
  // only loads one file.
  const { rows, loading, error } = useData<ScreenerRow>("screener.json");

  if (loading) return <p>Loading...</p>;
  if (error) return <p className="error">{error}</p>;

  return (
    <div>
      <h1>Search</h1>
      <p className="meta">Not defined yet. For now, screened tickers.</p>

      <DataGrid rows={rows} columns={columns} />
    </div>
  );
}
