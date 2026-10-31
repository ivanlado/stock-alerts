import { useState, type ReactNode } from "react";

/**
 * The controls at the top of each alert page: sector, minimum drop, window.
 *
 * They are CONTROLLED components: none of them remembers its own value. The
 * page hands each one the current `value` and an `onChange` function, and the
 * control only reports clicks. The page keeps the values in the URL (see
 * `useUrlParam` in lib/filters.ts), so they survive a reload.
 */

/** One row of filters, laid out by `.filters` in index.css. */
export function FilterBar({ children }: { children: ReactNode }) {
  return <div className="filters">{children}</div>;
}

/** A label above a control, so each group of buttons says what it filters. */
function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="filter">
      <span className="filter-label">{label}</span>
      {children}
    </div>
  );
}

/**
 * The sectors as a row of chips, any number of them on at once.
 *
 * A click toggles one sector; "All" clears the choice, which is the same as
 * having every sector on. `aria-pressed` tells a screen reader that each chip
 * is an on/off switch, not a plain button.
 */
export function SectorPicker({
  sectors,
  value,
  onChange,
}: {
  sectors: string[];
  value: string[];
  onChange: (value: string[]) => void;
}) {
  // A sector that came from the URL but has no company today is still listed,
  // otherwise it would be applied without any chip showing it.
  const options = [...value.filter((s) => !sectors.includes(s)), ...sectors];

  function toggle(sector: string) {
    // `.filter` drops the sector if it was on; otherwise it is added.
    onChange(value.includes(sector) ? value.filter((s) => s !== sector) : [...value, sector]);
  }

  return (
    <Field label="Sector">
      <div className="chips">
        <button
          type="button"
          className={value.length === 0 ? "chip active" : "chip"}
          aria-pressed={value.length === 0}
          onClick={() => onChange([])}
        >
          All
        </button>
        {options.map((sector) => (
          <button
            key={sector}
            type="button"
            className={value.includes(sector) ? "chip active" : "chip"}
            aria-pressed={value.includes(sector)}
            onClick={() => toggle(sector)}
          >
            {sector}
          </button>
        ))}
      </div>
    </Field>
  );
}

/**
 * A row of buttons where exactly one is active, e.g. the time windows.
 *
 * `<Value extends string>` is a generic: the caller's option values keep their
 * exact type (say, "var_1m" | "var_3m"), so `onChange` hands back one of THOSE
 * rather than any string.
 */
export function ButtonPicker<Value extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: Value; label: string }[];
  value: Value;
  onChange: (value: Value) => void;
}) {
  return (
    <Field label={label}>
      <div className="range-picker">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            className={option.value === value ? "range active" : "range"}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
    </Field>
  );
}

/**
 * The minimum drop: a few fixed buttons and a last one to type any number.
 *
 * `value` is the text stored in the URL: "" for "Any", "15" for 15%. Typing
 * reports every keystroke, so the cards update as the number is written.
 *
 * `useState` remembers one thing the URL does not: whether the box for typing
 * is open. It starts open when the URL already holds a number that is not one
 * of the buttons, e.g. after reloading a page filtered at 12%.
 */
export function MinimumPicker({
  label,
  presets,
  value,
  onChange,
}: {
  label: string;
  presets: number[];
  value: string;
  onChange: (value: string) => void;
}) {
  const isPreset = value === "" || presets.map(String).includes(value);
  const [custom, setCustom] = useState(!isPreset);

  function choose(preset: string) {
    setCustom(false);
    onChange(preset);
  }

  const buttons = [{ value: "", label: "Any" }, ...presets.map((p) => ({ value: String(p), label: `${p}%` }))];

  return (
    <Field label={label}>
      <div className="range-picker">
        {buttons.map((button) => (
          <button
            key={button.value}
            type="button"
            className={!custom && button.value === value ? "range active" : "range"}
            onClick={() => choose(button.value)}
          >
            {button.label}
          </button>
        ))}
        <button
          type="button"
          className={custom ? "range active" : "range"}
          onClick={() => setCustom(true)}
        >
          Custom
        </button>
        {custom && (
          <label className="custom-minimum">
            <input
              type="number"
              min={0}
              step={1}
              inputMode="decimal"
              // `autoFocus` puts the cursor in the box as soon as it appears.
              autoFocus
              value={value}
              onChange={(event) => onChange(event.target.value)}
              aria-label={`${label}, custom value in percent`}
            />
            %
          </label>
        )}
      </div>
    </Field>
  );
}

/**
 * How many cards the filters left, out of how many alerts. Shared by both alert
 * pages.
 */
export function Results({ count, total }: { count: number; total: number }) {
  if (total === 0) return <p className="muted">No company fired this alert today.</p>;
  if (count === 0) return <p className="muted">No company matches these filters.</p>;
  return (
    <p className="meta">
      Showing {count} of {total}
    </p>
  );
}
