"""
wiki_tickers.py
===============
Funciones para obtener los tickers de índices bursátiles desde Wikipedia.

Pensado para importarse desde otro proyecto:

    from wiki_tickers import get_tickers, scrape_tickers

    sp500 = get_tickers("sp500")        # por nombre (usa el registro INDICES)
    ibex  = get_tickers("ibex35")

    # o directamente por URL, sin tocar el registro:
    otros = scrape_tickers(
        "https://es.wikipedia.org/wiki/FTSE_100",
        ticker_headers=["ticker", "símbolo", "epic"],
        expected_rows=100,
    )

Requisitos:
    pip install pandas lxml requests
"""

from __future__ import annotations

from io import StringIO

import pandas as pd
import requests

# Wikipedia devuelve 403 sin un User-Agent de navegador real.
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

# Registro de índices conocidos. Añade aquí los que vayas necesitando.
INDICES: dict[str, dict] = {
    "sp500": {
        "url": "https://es.wikipedia.org/wiki/Anexo:Compa%C3%B1%C3%ADas_del_S%26P_500",
        "ticker_headers": ["símbolo", "simbolo", "symbol", "ticker"],
        "expected_rows": 503,
    },
    "ibex35": {
        "url": "https://es.wikipedia.org/wiki/IBEX_35",
        "ticker_headers": ["ticker", "símbolo", "simbolo", "código", "codigo"],
        "expected_rows": 35,
        "suffix": ".MC",
    },
}


def scrape_tickers(
    url: str,
    ticker_headers: list[str],
    expected_rows: int | None = None,
    timeout: int = 30,
    suffix: str | None = None,
) -> list[str]:
    """Descarga una página de Wikipedia y devuelve la lista de tickers.

    Parámetros
    ----------
    url:
        Enlace exacto a la página de Wikipedia.
    ticker_headers:
        Posibles nombres (en minúsculas) de la columna del ticker. Se compara
        con startswith(), así que "símbolo" cubre "símbolo bursátil", etc.
    expected_rows:
        Nº aproximado de componentes. Desempata si varias tablas tienen una
        columna de ticker (p. ej. la tabla de composición frente a una de
        historial de cambios).
    timeout:
        Segundos de espera para la petición HTTP.

    Devuelve
    --------
    list[str]
        Los tickers, ya limpios (sin notas al pie ni espacios).

    Lanza
    -----
    requests.HTTPError
        Si la descarga falla.
    ValueError
        Si no se encuentra ninguna columna de ticker.
    """
    resp = requests.get(url, headers=_HEADERS, timeout=timeout)
    resp.raise_for_status()
    tables = pd.read_html(StringIO(resp.text))

    table, ticker_col = _find_ticker_table(tables, ticker_headers, expected_rows)
    tickers = _clean_tickers(table[ticker_col])
    if suffix:
        tickers = [t + suffix for t in tickers]
    return tickers


def get_tickers(index_name: str) -> list[str]:
    """Devuelve los tickers de un índice registrado en INDICES.

    Ejemplo: get_tickers("sp500") -> ["MMM", "AOS", ...]
    """
    if index_name not in INDICES:
        disponibles = ", ".join(INDICES)
        raise KeyError(
            f"'{index_name}' no está en INDICES. Disponibles: {disponibles}"
        )
    cfg = INDICES[index_name]
    return scrape_tickers(
        cfg["url"],
        ticker_headers=cfg["ticker_headers"],
        expected_rows=cfg.get("expected_rows"),
        suffix=cfg.get("suffix"),
    )


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------
def _find_ticker_table(
    tables: list[pd.DataFrame],
    ticker_headers: list[str],
    expected_rows: int | None = None,
) -> tuple[pd.DataFrame, object]:
    """Elige (tabla, columna) cuya cabecera coincide con ticker_headers."""
    matches: list[tuple[pd.DataFrame, object]] = []
    for table in tables:
        for col in table.columns:
            name = str(col).strip().lower()
            if any(name.startswith(key) for key in ticker_headers):
                matches.append((table, col))
                break
    if not matches:
        raise ValueError("No se encontró ninguna columna de ticker.")
    if expected_rows is not None:
        matches.sort(key=lambda m: abs(len(m[0]) - expected_rows))
    return matches[0]


def _clean_tickers(series: pd.Series) -> list[str]:
    """Quita notas al pie [1], espacios y celdas vacías/NaN."""
    cleaned = (
        series.astype(str)
        .str.replace(r"\[.*?\]", "", regex=True)
        .str.strip()
    )
    return [t for t in cleaned.tolist() if t and t.lower() != "nan"]