"""DuckDB connection helpers: load the raw extract and run the project's SQL files in order."""

from __future__ import annotations

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "online_retail_ii_text.parquet"
SQL = ROOT / "sql"


def run_sql(con: duckdb.DuckDBPyConnection, name: str) -> None:
    con.execute((SQL / name).read_text())


def staged(raw_path: Path | str = RAW) -> duckdb.DuckDBPyConnection:
    """A connection holding `raw` and the staged `lines` table and `product_lines` view."""
    con = duckdb.connect()
    con.execute(f"CREATE TABLE raw AS SELECT * FROM read_parquet('{raw_path}')")
    run_sql(con, "01_staging.sql")
    return con
