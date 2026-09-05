import { HashRouter, Link, Route, Routes } from "react-router-dom";
import { AlertsPage } from "./routes/AlertsPage";
import { SearchPage } from "./routes/SearchPage";

/**
 * App layout: navigation menu plus one route per page.
 *
 * ROUTING BASICS. A single-page app never reloads the browser. React Router
 * watches the URL and swaps which component is displayed:
 *   - `HashRouter`   reads the part of the URL after `#` (e.g. `/#/search`).
 *   - `Routes`       picks the first `Route` whose `path` matches the URL.
 *   - `Route`        maps one path to the component to display.
 *   - `Link`         like an `<a>` tag, but changes the URL without reloading.
 *
 * We use HashRouter (not BrowserRouter) because GitHub Pages returns a 404
 * when reloading a normal route: it looks for a file that does not exist.
 * Everything after `#` never reaches the server, which sidesteps the problem.
 * On a real server, swapping in BrowserRouter is the only change needed.
 *
 * JSX NOTE: the HTML-looking syntax below is JSX. It is not HTML, it compiles
 * to JavaScript, which is why an attribute is `className` and not `class`.
 *
 * To add a page: create a file in `routes/`, then add a `Link` and a `Route`.
 */
export function App() {
  return (
    <HashRouter>
      <nav>
        <Link to="/">Alerts</Link>
        <Link to="/search">Search</Link>
      </nav>

      <main>
        <Routes>
          <Route path="/" element={<AlertsPage />} />
          <Route path="/search" element={<SearchPage />} />
        </Routes>
      </main>
    </HashRouter>
  );
}
