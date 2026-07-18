from __future__ import annotations

import json
from pathlib import Path

TICKERS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "tickers"


def load_tickers() -> list[str]:
    tickers = []
    for path in sorted(TICKERS_DIR.glob("*.json")):
        with open(path) as f:
            tickers.extend(json.load(f))
    return list(dict.fromkeys(tickers))


