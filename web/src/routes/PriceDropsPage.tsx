import { useMemo } from "react";
import { CompanyCards, type CardBadge } from "../components/CompanyCards";
import { ButtonPicker, FilterBar, MinimumPicker, Results, SectorPicker } from "../components/Filters";
import { useData } from "../lib/data";
import {
  joinSectors,
  parseMinimum,
  parseSectors,
  rankCompanies,
  sectorsOf,
  useUrlParam,
} from "../lib/filters";
import type { CompanyCard } from "../lib/types";
import { DEFAULT_WINDOW, PRICE_WINDOWS, windowLabel, type PriceWindowKey } from "../lib/windows";

/** The minimum-drop buttons, besides "Any" and "Custom". */
const MINIMUM_PRESETS = [5, 10, 15, 20];

/** The asset-type buttons. "" (all) is the default, so it stays out of the URL. */
type AssetFilter = "" | "stock" | "fund";
const TYPE_OPTIONS: { value: AssetFilter; label: string }[] = [
  { value: "", label: "All" },
  { value: "stock", label: "Stocks" },
  { value: "fund", label: "Funds" },
];

/** The window buttons, in the shape ButtonPicker expects. */
const WINDOW_OPTIONS = PRICE_WINDOWS.map((w) => ({ value: w.key, label: w.label }));

/**
 * Reads the window from the URL, falling back to the default for anything
 * that is not one of ours -- a hand-edited URL must not break the page.
 */
function toWindow(text: string): PriceWindowKey {
  return PRICE_WINDOWS.some((w) => w.key === text) ? (text as PriceWindowKey) : DEFAULT_WINDOW;
}

/**
 * Price drops: the companies that fired the price rule, ranked by how much
 * they fell over the chosen window.
 *
 * A company is here if it dropped past the threshold in ANY window, so with
 * the minimum at "Any" a company that only fell hard today still shows up
 * when ranking by 3M -- just further down. Raising the minimum is what hides it.
 */
export function PriceDropsPage() {
  const companies = useData<CompanyCard>("companies.json");
  const [sectorText, setSectorText] = useUrlParam("sector", "");
  const sectors = parseSectors(sectorText);
  const [minimum, setMinimum] = useUrlParam("min", "");
  const [windowText, setWindow] = useUrlParam("window", DEFAULT_WINDOW);
  const selected = toWindow(windowText);
  const [typeText, setType] = useUrlParam("type", "");
  // Anything that is not one of the options (a hand-edited URL) means "all".
  const assetType: AssetFilter = typeText === "stock" || typeText === "fund" ? typeText : "";

  // `useMemo` recomputes only when a value in its list changes; see AnalystPage.
  const alerted = useMemo(() => companies.rows.filter((c) => c.price_alert), [companies.rows]);
  // The type filter narrows the list BEFORE the sector chips are built from
  // it, so choosing "Funds" leaves no company sectors to pick from.
  const ofType = useMemo(
    () => (assetType === "" ? alerted : alerted.filter((c) => c.asset_type === assetType)),
    [alerted, assetType],
  );
  const shown = useMemo(
    () => rankCompanies(ofType, (c) => c[selected], { sectors, minimum: parseMinimum(minimum) }),
    [ofType, selected, sectorText, minimum],
  );

  // The card leads with the window being ranked by, drawn larger, then the
  // gap to the analyst target for context.
  const badges: CardBadge[] = useMemo(
    () => [
      { label: windowLabel(selected), value: (c) => c[selected] },
      { label: "vs target", value: (c) => c.pct_price_diff },
    ],
    [selected],
  );

  if (companies.loading) return <p>Loading...</p>;
  if (companies.error) return <p className="error">{companies.error}</p>;

  return (
    <div>
      <h1>Price drops</h1>
      <p className="meta">
        Companies and index funds whose price fell past the alert threshold in at
        least one window, biggest drop over the chosen window first. Generated at: {companies.generatedAt}
      </p>

      <FilterBar>
        <ButtonPicker label="Type" options={TYPE_OPTIONS} value={assetType} onChange={setType} />
        <SectorPicker
          sectors={sectorsOf(ofType)}
          value={sectors}
          onChange={(chosen) => setSectorText(joinSectors(chosen))}
        />
        <ButtonPicker label="Window" options={WINDOW_OPTIONS} value={selected} onChange={setWindow} />
        <MinimumPicker
          label={`Min. drop over ${windowLabel(selected)}`}
          presets={MINIMUM_PRESETS}
          value={minimum}
          onChange={setMinimum}
        />
      </FilterBar>

      <Results count={shown.length} total={alerted.length} />
      <CompanyCards rows={shown} badges={badges} />
    </div>
  );
}
