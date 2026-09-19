/**
 * How numbers are written and coloured across the whole dashboard.
 *
 * WHY A SEPARATE FILE. The same percentage shows up in a table cell, in a
 * chart tooltip and on a company card. Keeping the rounding and the colour
 * rule here means they cannot drift apart: change the scale once and every
 * view follows.
 */

/** Every number the user sees is rounded to this many decimals. */
const DECIMALS = 1;

/** What is shown instead of a number that Python exported as null. */
export const MISSING = "—";

/**
 * Where the colour gradient saturates, in percent.
 *
 * The scale is FIXED, not relative to the values on screen: a -20% always
 * paints the same red whatever else is in the table. That is what makes the
 * colour comparable between the two tables and between one day and the next.
 * Anything beyond ±20% is simply drawn at full strength.
 */
const SATURATION = 20;

/**
 * Rounds to one decimal. Returns MISSING for null, undefined or NaN.
 *
 * `value == null` is true for BOTH null and undefined -- the one place in
 * JavaScript where the loose `==` is worth using on purpose.
 */
export function formatNumber(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return MISSING;
  return value.toFixed(DECIMALS);
}

/** Same as formatNumber, with a percent sign. */
export function formatPercent(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return MISSING;
  return `${value.toFixed(DECIMALS)}%`;
}

/** The CSS properties a variation cell or badge gets painted with. */
export type VariationStyle = {
  backgroundColor: string;
  color: string;
};

/**
 * Green for a rise, red for a drop, stronger the bigger the move.
 *
 * The opacity carries the magnitude: a value at or beyond ±SATURATION is drawn
 * at full strength, and everything below is drawn proportionally lighter, so 0%
 * comes out transparent. Text flips to white on the darker half of the scale,
 * because dark grey on saturated green is hard to read.
 */
export function variationStyle(value: number | null | undefined): VariationStyle {
  if (value == null || Number.isNaN(value)) {
    return { backgroundColor: "transparent", color: "#999" };
  }

  // `Math.min(x, 1)` caps the ratio at 1 so beyond the saturation point the
  // colour stops getting darker instead of overflowing.
  const intensity = Math.min(Math.abs(value) / SATURATION, 1);
  const [r, g, b] = value >= 0 ? [22, 163, 74] : [220, 38, 38];

  return {
    backgroundColor: `rgba(${r}, ${g}, ${b}, ${(intensity * 0.85).toFixed(3)})`,
    color: intensity > 0.5 ? "#fff" : "#1a1a1a",
  };
}
