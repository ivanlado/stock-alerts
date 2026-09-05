"""Turns a Snapshot into the plain-text body of the alert email."""

import pandas as pd

from pipeline import Snapshot


def format_analyst_alerts(alerts: pd.DataFrame) -> str:
    lines = [
        f"{row['ticker']} ({row['short_name']}): "
        f"Current={row['current']} | Median={row['median']} | "
        f"Diff={row['price_diff']:.2f} | Pct Diff={row['pct_price_diff']:.1f}%"
        for _, row in alerts.iterrows()
    ]
    return "\n".join(lines)


def format_price_alerts(alerts: pd.DataFrame) -> str:
    lines = [
        f"{row['ticker']} ({row['short_name']}): "
        f"1M={row['var_1m']:.2f}% | 3M={row['var_3m']:.2f}% | "
        f"6M={row['var_6m']:.2f}% | 9M={row['var_9m']:.2f}%"
        for _, row in alerts.iterrows()
    ]
    return "\n".join(lines)


def format_snapshot(snapshot: Snapshot) -> str:
    """Full email body. Empty string when there is nothing to report."""
    sections = []

    if not snapshot.analyst_alerts.empty:
        sections.append(format_analyst_alerts(snapshot.analyst_alerts))

    if not snapshot.price_alerts.empty:
        sections.append(format_price_alerts(snapshot.price_alerts))

    return "\n\n".join(sections)
