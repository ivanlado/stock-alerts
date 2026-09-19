import { useEffect, useState } from "react";

/**
 * The single breakpoint of the project: below this width (a phone held
 * upright, roughly) the layout switches to its compact variant.
 *
 * The same number lives in the `@media` block of index.css. CSS handles what
 * is purely visual (paddings, font sizes); this hook handles what JavaScript
 * decides (which grid columns exist, how tall a chart is).
 */
export const NARROW_WIDTH = 640;

/**
 * Returns `true` while the window is narrower than NARROW_WIDTH, and repaints
 * the component whenever that changes (rotating a phone, resizing a window).
 *
 * TWO REACT TOOLS ARE USED HERE:
 *
 *  - `useState(initial)` keeps a value between repaints AND asks React to
 *    repaint when it is set. `[value, setValue]` is the pair it returns.
 *  - `useEffect(fn, [])` runs `fn` once, after the first paint, and returns a
 *    cleanup function React calls when the component disappears.
 *
 * `window.matchMedia(query)` is the browser's own API for CSS media queries:
 * `.matches` is true or false right now, and it fires an event on every
 * change, so there is no need to listen to every pixel of a resize.
 */
export function useIsNarrow(): boolean {
  const query = `(max-width: ${NARROW_WIDTH}px)`;

  // The initial value is read synchronously so the first paint is already
  // correct, instead of flashing the wide layout for an instant.
  const [isNarrow, setIsNarrow] = useState(() => window.matchMedia(query).matches);

  useEffect(() => {
    const media = window.matchMedia(query);
    const update = () => setIsNarrow(media.matches);

    update(); // in case the width changed between the first paint and here
    media.addEventListener("change", update);

    return () => media.removeEventListener("change", update);
  }, [query]);

  return isNarrow;
}
