import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Vite is the build tool. It serves the app during development (`npm run dev`,
 * with instant reload on save) and bundles it into plain HTML/CSS/JS files
 * inside `dist/` for production (`npm run build`).
 *
 * The react plugin teaches it to compile JSX -- the HTML-like syntax used in
 * .tsx files, which browsers do not understand on their own.
 */
export default defineConfig({
  plugins: [react()],
  // Relative asset paths, so the build works on GitHub Pages without knowing
  // the repository name (the site is served from /<repo>/, not from /).
  base: "./",
});
