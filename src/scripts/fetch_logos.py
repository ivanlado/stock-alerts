"""Downloads a logo for every stock and fund into ``web/public/logos/``.

Run by hand, from ``src/``::

    python -m scripts.fetch_logos            # only the tickers without a logo
    python -m scripts.fetch_logos --force    # every ticker again
    python -m scripts.fetch_logos --shrink-only  # re-encode at SIZE, no download

The logos come from Financial Modeling Prep's public image endpoint, which
serves one PNG per ticker with no key, for US and Spanish stocks and for the
ETFs (the issuer's logo). They are saved into the repository rather than
linked from the page: the dashboard then works if that service goes away, and
the people reading it are not sent to a third party on every visit.

Each logo is shrunk to fit ``SIZE`` pixels: the service sends up to 250px
and ~100KB, the page draws them at 40px at most, and 96 covers a high-density
screen at twice that.

A logo changes about once a decade, so this is not part of the daily job.
``export/json_export.py`` points each row at its file when one exists; a
ticker without one gets its initials in the web.
"""

import io
import json
import random
import sys
import time
from pathlib import Path

import requests
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
TICKERS_DIR = REPO_ROOT / "data" / "tickers"
FUNDS_PATH = REPO_ROOT / "data" / "funds.json"
LOGOS_DIR = REPO_ROOT / "web" / "public" / "logos"

LOGO_URL = "https://financialmodelingprep.com/image-stock/{ticker}.png"

# Below this many bytes the "image" is an error page or a blank placeholder.
MIN_BYTES = 200

# The longest side of a saved logo, in pixels.
SIZE = 96


def _shrink(content: bytes) -> bytes:
    """The image resized to fit SIZE x SIZE (never enlarged), as an optimised PNG."""
    image = Image.open(io.BytesIO(content))
    image.thumbnail((SIZE, SIZE))
    out = io.BytesIO()
    image.save(out, format="PNG", optimize=True)
    return out.getvalue()


def _tickers() -> list[str]:
    tickers: list[str] = []
    for path in sorted(TICKERS_DIR.glob("*.json")):
        tickers.extend(json.loads(path.read_text()))
    tickers.extend(json.loads(FUNDS_PATH.read_text()))
    return list(dict.fromkeys(tickers))


def fetch_logo(ticker: str) -> bytes | None:
    """The PNG for one ticker, or None when the service has none."""
    response = requests.get(LOGO_URL.format(ticker=ticker), timeout=20)
    is_image = response.headers.get("content-type", "").startswith("image/")
    if response.status_code != 200 or not is_image or len(response.content) < MIN_BYTES:
        return None
    return response.content


def main() -> None:
    force = "--force" in sys.argv
    LOGOS_DIR.mkdir(parents=True, exist_ok=True)
    if "--shrink-only" in sys.argv:
        # Re-encodes the logos already on disk, after a change of SIZE.
        for path in LOGOS_DIR.glob("*.png"):
            path.write_bytes(_shrink(path.read_bytes()))
        print("Shrunk the logos on disk")
        return

    tickers = _tickers()
    pending = [t for t in tickers if force or not (LOGOS_DIR / f"{t}.png").exists()]
    print(f"{len(pending)} of {len(tickers)} tickers to fetch")

    missing: list[str] = []
    for ticker in pending:
        time.sleep(random.uniform(0.1, 0.4))
        try:
            content = fetch_logo(ticker)
        except Exception as e:
            print(f"{ticker}: {type(e).__name__}: {e}")
            content = None
        if content is None:
            missing.append(ticker)
            continue
        (LOGOS_DIR / f"{ticker}.png").write_bytes(_shrink(content))

    print(f"Saved {len(pending) - len(missing)}; no logo for {len(missing)}: {missing}")


if __name__ == "__main__":
    main()
