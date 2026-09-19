# Run archive

Parquet archive of every pipeline run, written by the daily GitHub Actions job
(`export/history_export.py` on `master`). One file per table and day:

    runs/YYYY-MM-DD.parquet             when it ran and what it found
    screener/YYYY-MM-DD.parquet
    analyst_alerts/YYYY-MM-DD.parquet
    price_alerts/YYYY-MM-DD.parquet
    fundamentals/YYYY-MM-DD.parquet

This branch holds data only, never code, so the daily commit does not show up
in the code history. Every file starts with `snapshot_date` and `generated_at`,
so reading a table across time is one glob:

    SELECT * FROM 'history/analyst_alerts/*.parquet'
