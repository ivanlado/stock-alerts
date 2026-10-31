import { HashRouter, NavLink, Route, Routes } from "react-router-dom";
import { AnalystPage } from "./routes/AnalystPage";
import { PriceDropsPage } from "./routes/PriceDropsPage";
import { SearchPage } from "./routes/SearchPage";
import { SummaryPage } from "./routes/SummaryPage";

/**
 * App layout: navigation menu plus one route per page.
 *
 * ROUTING BASICS. A single-page app never reloads the browser. React Router
 * watches the URL and swaps which component is displayed:
 *   - `HashRouter`   reads the part of the URL after `#` (e.g. `/#/search`).
 *   - `Routes`       picks the first `Route` whose `path` matches the URL.
 *   - `Route`        maps one path to the component to display.
 *   - `NavLink`      like an `<a>` tag, but changes the URL without reloading,
 *                    and marks itself `active` while its page is showing, which
 *                    is what underlines the current page in the menu.
 *
 * We use HashRouter (not BrowserRouter) because GitHub Pages returns a 404
 * when reloading a normal route: it looks for a file that does not exist.
 * Everything after `#` never reaches the server, which sidesteps the problem.
 * On a real server, swapping in BrowserRouter is the only change needed.
 *
 * JSX NOTE: the HTML-looking syntax below is JSX. It is not HTML, it compiles
 * to JavaScript, which is why an attribute is `className` and not `class`.
 *
 * `end` on the Summary link makes it active only on `/` exactly: without it,
 * every path would count, since every path starts with `/`.
 *
 * To add a page: create a file in `routes/`, then add a `NavLink` and a `Route`.
 */
export function App() {
  return (
    <HashRouter>
      <nav>
        <NavLink to="/" end>
          Summary
        </NavLink>
        <NavLink to="/analyst">Analyst alerts</NavLink>
        <NavLink to="/price-drops">Price drops</NavLink>
        <NavLink to="/search">Search</NavLink>
      </nav>

      <main>
        <Routes>
          <Route path="/" element={<SummaryPage />} />
          <Route path="/analyst" element={<AnalystPage />} />
          <Route path="/price-drops" element={<PriceDropsPage />} />
          <Route path="/search" element={<SearchPage />} />
        </Routes>
      </main>
    </HashRouter>
  );
}
