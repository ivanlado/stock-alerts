import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./index.css";

/**
 * Entry point of the whole frontend. Vite loads this file from index.html.
 *
 * `createRoot` connects React to a plain DOM element: from now on React owns
 * everything inside `<div id="root">` and paints it. The `!` after
 * `getElementById` is TypeScript's "non-null assertion": that method may
 * return null, and `!` tells the compiler "trust me, this element exists".
 *
 * `StrictMode` is a development-only helper. It renders every component twice
 * to surface bugs early, so DO NOT be surprised to see duplicated network
 * requests or logs while developing. It disappears in the production build.
 *
 * Importing the CSS file from TypeScript looks odd but is how Vite works:
 * it detects the import and injects the stylesheet into the page.
 */
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
