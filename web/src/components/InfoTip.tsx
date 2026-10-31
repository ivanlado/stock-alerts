import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";

/** Width of the explanation box, in pixels; matches `.info-text` in index.css. */
const BOX_WIDTH = 272;

/**
 * A small "i" button that shows a short explanation, for readers who do not
 * know what a metric means. It opens on hover, on focus and on click (a tap
 * on a phone, where there is no hover), and closes when the pointer or the
 * focus leaves it.
 *
 * WHY A PORTAL. The button also sits inside table headers, and a table header
 * cuts off anything that overflows it. `createPortal` draws the box as a
 * direct child of `<body>` instead, outside the header, and `position: fixed`
 * places it under the button using the button's position on screen
 * (`getBoundingClientRect`). It closes on scroll, where that position would go
 * stale.
 *
 * Hooks used: `useState` remembers where the box is (null while closed);
 * `useRef` holds the button element itself, to measure it; `useId` gives an id
 * unique on the page, which links button and text for screen readers;
 * `useEffect` attaches browser listeners and removes them again on cleanup.
 */
export function InfoTip({ label, text }: { label: string; text: string }) {
  const id = useId();
  const button = useRef<HTMLButtonElement>(null);
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null);

  function open() {
    const box = button.current?.getBoundingClientRect();
    if (!box) return;
    // Kept inside the window: a button near the right edge opens leftwards.
    const left = Math.max(8, Math.min(box.left - 8, window.innerWidth - BOX_WIDTH - 8));
    setPosition({ top: box.bottom + 6, left });
  }

  function close() {
    setPosition(null);
  }

  // A click on the button must not reach whatever contains it: in a table
  // header that would also sort the column. The grid listens with plain
  // browser listeners, which React's own `stopPropagation` runs too late to
  // stop, so the button gets a plain listener of its own.
  useEffect(() => {
    const element = button.current;
    if (!element) return;
    const stop = (event: Event) => event.stopPropagation();
    element.addEventListener("click", stop);
    element.addEventListener("mousedown", stop);
    return () => {
      element.removeEventListener("click", stop);
      element.removeEventListener("mousedown", stop);
    };
  }, []);

  // While open, any scroll closes it rather than leaving it floating.
  useEffect(() => {
    if (!position) return;
    window.addEventListener("scroll", close, true);
    return () => window.removeEventListener("scroll", close, true);
  }, [position]);

  return (
    <>
      <button
        ref={button}
        type="button"
        className="info-button"
        aria-label={`About ${label}`}
        aria-describedby={position ? id : undefined}
        onMouseEnter={open}
        onMouseLeave={close}
        onFocus={open}
        onBlur={close}
        onClick={open}
      >
        i
      </button>
      {position &&
        createPortal(
          <span role="tooltip" id={id} className="info-text" style={position}>
            {text}
          </span>,
          document.body,
        )}
    </>
  );
}
