"""Adds the LLM-written commentary to the alert DataFrames.

One column is appended to every alert table:
  - ``explanation``: why this particular alert fired, today

It is the volatile half of the commentary, asked on every run because a reason
from last month is a wrong reason. What a company IS -- its business, its moat,
its competitors -- does not move daily and lives in ``profiles.py``, cached on
disk.

It is plain data, like any other column, so both sinks pick it up for free:
``export/`` writes it into the JSON the web reads, and ``notifications/`` could
put it in the email.

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


def add_commentary(alerts: pd.DataFrame, explanation: Prompt) -> pd.DataFrame:
    """Returns ``alerts`` with the ``explanation`` column added.

    ``explanation`` is the prompt matching this table's alert rule.
    """
    if alerts.empty:
        return alerts

    alerts = alerts.copy()
    explanations: list[str | None] = []

    for _, row in alerts.iterrows():
        name = row.get("short_name") or str(row["ticker"])
        explanations.append(_answer(explanation, **{**row.to_dict(), "name": name}))

    alerts["explanation"] = explanations
    return alerts
