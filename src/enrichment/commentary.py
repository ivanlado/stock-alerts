"""Adds the LLM-written commentary to the alert DataFrames.

Two columns are appended to every alert table:
  - ``business``:    what the company does and where its revenue comes from
  - ``explanation``: why this particular alert fired

They are plain data, like any other column, so both sinks pick them up for
free: ``export/`` writes them into the JSON the web reads, and ``notifications/``
could put them in the email.

An LLM call is the only step of the pipeline that can fail for reasons outside
the code -- a quota, a timeout, an unreachable Ollama. None of that should
bring down the daily run, so a failed call leaves the cell empty and the
pipeline carries on.
"""

import pandas as pd

from enrichment import prompts
from enrichment.prompts import Prompt
from utils.llm import ask


def _readable(key: str, value: object) -> str:
    """Formats one value the way it should appear inside a prompt.

    Columns holding a percentage (``var_1m``, ``pct_price_diff``, ...) carry
    their own ``%`` sign, so the templates do not have to add one. That is what
    keeps a missing value reading as "unknown" rather than "unknown%".
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "unknown"
    if isinstance(value, float):
        suffix = "%" if key.startswith(("var_", "pct_")) else ""
        return f"{value:.1f}{suffix}"
    return str(value)


def _answer(prompt: Prompt, **values: object) -> str | None:
    """Renders a prompt, asks it, and returns None if the call fails."""
    rendered = prompt.render(**{k: _readable(k, v) for k, v in values.items()})
    try:
        return ask(rendered, system=prompts.SYSTEM, web_search=prompt.web_search)
    except Exception as e:
        print(f"LLM call failed ({type(e).__name__}): {e}")
        return None


def add_commentary(
    alerts: pd.DataFrame,
    explanation: Prompt,
    business_cache: dict[str, str | None] | None = None,
) -> pd.DataFrame:
    """Returns ``alerts`` with the ``business`` and ``explanation`` columns.

    ``explanation`` is the prompt matching this table's alert rule.
    ``business_cache`` is shared between tables so that a ticker triggering both
    alerts is described once rather than twice.
    """
    if alerts.empty:
        return alerts

    cache = {} if business_cache is None else business_cache
    alerts = alerts.copy()

    businesses: list[str | None] = []
    explanations: list[str | None] = []

    for _, row in alerts.iterrows():
        ticker = str(row["ticker"])
        name = row.get("short_name") or ticker
        values = {**row.to_dict(), "name": name}

        if ticker not in cache:
            cache[ticker] = _answer(prompts.BUSINESS, name=name, ticker=ticker)
        businesses.append(cache[ticker])

        explanations.append(_answer(explanation, **values))

    alerts["business"] = businesses
    alerts["explanation"] = explanations
    return alerts
