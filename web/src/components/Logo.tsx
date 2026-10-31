import { useState } from "react";

/**
 * A company's logo in a small rounded square, or its initials when there is
 * no logo.
 *
 * `src` is the path Python exported (`logos/<ticker>.png`), relative so it
 * works wherever the site is served from, or null when no logo was fetched.
 * `useState` remembers whether the image failed to load -- a file removed
 * after the JSON was written, say -- so the initials step in instead of the
 * browser's broken-image icon.
 *
 * `alt=""` marks the image as decoration: the ticker is written right beside
 * it, and a screen reader would otherwise read the name twice.
 */
export function Logo({
  ticker,
  src,
  size = 28,
}: {
  ticker: string;
  src: string | null;
  size?: number;
}) {
  const [failed, setFailed] = useState(false);
  // Inline because the size is a prop: the same component draws the 20px
  // table logo and the 40px one in the detail panel.
  const box = { width: size, height: size };

  if (!src || failed) {
    // "ITX.MC" -> "IT": the market suffix says nothing about the company.
    const initials = ticker.replace(/\..*$/, "").slice(0, 2);
    return (
      <span className="logo logo-initials" style={{ ...box, fontSize: size * 0.4 }} aria-hidden>
        {initials}
      </span>
    );
  }

  return (
    <img
      className="logo"
      style={box}
      src={src}
      alt=""
      // The browser only downloads a logo when it comes near the screen,
      // which matters in a table of five hundred rows.
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}
