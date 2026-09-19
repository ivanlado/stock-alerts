"""Archives every run as Parquet, one file per table and day.

``json_export.py`` writes a *snapshot*: it always describes today and the next
run overwrites it. This module is the opposite. It only ever overwrites today's
own files, so runs accumulate into a history that can be queried later.

It exists because most of what a run produces cannot be recovered afterwards.
Prices can be fetched again for any past date, but the analysts' price target
as it stood today, which companies passed the screener today and what the LLM
wrote about them today are point-in-time facts: a day that is not archived is
lost for good. That is why this sink is worth having long before anything
reads from it.

Layout (``history/`` at the repo root, kept on its own ``data`` branch)::

    history/
      runs/2026-09-19.parquet             one row: when it ran, what it found
      screener/2026-09-19.parquet
      analyst_alerts/2026-09-19.parquet
      price_alerts/2026-09-19.parquet
      fundamentals/2026-09-19.parquet

Parquet rather than JSON for two reasons. It is columnar and compressed, and
these tables repeat sectors, tickers and descriptions constantly, so they
shrink to a fraction of the JSON size. And a reader can pull single columns out
of it without loading the whole file, which is what would let a future history
page query years of runs straight from the browser, with no backend.

Every file carries ``snapshot_date`` and ``generated_at`` as its first two
columns, so reading a whole table across time is just::

    SELECT * FROM 'history/analyst_alerts/*.parquet'
"""

import os
from pathlib import Path

import pandas as pd

# Imported but never called on purpose. pandas loads pyarrow as the Parquet
# engine at runtime, so nothing in this file references it by name -- and
# pipreqs, which regenerates requirements.txt from the imports it can see,
# would drop it. Naming it here keeps it in requirements.txt and turns a
# missing install into a loud ImportError at startup instead of a silent
# archive that writes nothing, every day, unnoticed.
import pyarrow  # noqa: F401

from pipeline import Snapshot

REPO_ROOT = Path(__file__).resolve().parents[2]

# CI checks the ``data`` branch out into its own directory and points this
# variable at it, so the archive is written straight into the branch that
# stores it. Locally it defaults to ``history/`` at the repo root.
HISTORY_DIR = Path(os.environ.get("HISTORY_DIR") or REPO_ROOT / "history")


def _write_table(
    df: pd.DataFrame,
    out_dir: Path,
    name: str,
    snapshot_date: str,
    generated_at: pd.Timestamp,
) -> None:
    """Writes one table's file for one day, stamped with when it was produced.

    Re-running on the same day overwrites that day's file, which is what makes
    the job safe to retry.
    """
    if df.empty:
        # Not an error: some days nothing fires. ``runs/`` records that the run
        # happened anyway, so an absent file is never ambiguous.
        print(f"History: {name} is empty, nothing archived")
        return

    table = df.copy()
    table.insert(0, "snapshot_date", snapshot_date)
    table.insert(1, "generated_at", generated_at)

    path = out_dir / name / f"{snapshot_date}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        table.to_parquet(path, index=False, compression="zstd")
    except Exception as exc:
        # Same rule as the LLM commentary: a sink that fails leaves a gap in
        # the archive, it does not bring the run down. The email still goes out.
        print(f"History: could not archive {name}: {exc}")
        return

    print(f"Wrote {path.relative_to(out_dir)} ({len(table)} rows)")


def _run_summary(snapshot: Snapshot) -> pd.DataFrame:
    """One row describing the run itself.

    Written even when every other table is empty, so a day on which nothing
    fired can be told apart from a day the job never ran at all.
    """
    return pd.DataFrame(
        [
            {
                "screened": len(snapshot.screened),
                "analyst_alerts": len(snapshot.analyst_alerts),
                "price_alerts": len(snapshot.price_alerts),
            }
        ]
    )


def export_history(snapshot: Snapshot, out_dir: Path = HISTORY_DIR) -> None:
    """Appends this run to the Parquet archive under ``out_dir``."""
    snapshot_date = snapshot.generated_at.date().isoformat()
    generated_at = pd.Timestamp(snapshot.generated_at)

    tables = {
        "runs": _run_summary(snapshot),
        "screener": pd.DataFrame({"ticker": snapshot.screened}),
        "analyst_alerts": snapshot.analyst_alerts,
        "price_alerts": snapshot.price_alerts,
        "fundamentals": snapshot.fundamentals,
    }

    for name, df in tables.items():
        _write_table(df, out_dir, name, snapshot_date, generated_at)
