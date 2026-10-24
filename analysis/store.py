"""Read, write and validate the aggregate files the dashboard consumes.

The dashboard depends only on this module's contract (file names + columns),
never on how the aggregates were computed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .artists import ARTIST_METRIC_COLUMNS
from .entry import ENTRY_COLUMNS
from .segments import ARTIST_SEGMENT_COLUMNS
from .trends import WEEKLY_COLUMNS

MANIFEST = "manifest.json"
TABLE_COLUMNS = {
    "artist_metrics": ["population", *ARTIST_METRIC_COLUMNS],
    "artist_weekly": ["population", *WEEKLY_COLUMNS],
    "entry_tracks": ["population", *ENTRY_COLUMNS],
    "artist_segments": ["population", *ARTIST_SEGMENT_COLUMNS],
    "segment_users": ["population", "segment", "users", "window_listens", "share_of_listens"],
    "daily_coverage": ["listen_day", "listens", "listeners", "in_window"],
}


def validate_table(name: str, table: pd.DataFrame) -> None:
    expected = TABLE_COLUMNS[name]
    missing = [c for c in expected if c not in table.columns]
    if missing:
        raise ValueError(f"{name} is missing columns {missing}")


def write_aggregates(tables: dict[str, pd.DataFrame], manifest: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in TABLE_COLUMNS:
        table = tables[name]
        validate_table(name, table)
        table[TABLE_COLUMNS[name]].to_parquet(out_dir / f"{name}.parquet", index=False, compression="zstd")
    (out_dir / MANIFEST).write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")


def read_manifest(agg_dir: Path) -> dict:
    return json.loads((Path(agg_dir) / MANIFEST).read_text(encoding="utf-8"))


def read_table(agg_dir: Path, name: str, population: str | None = None) -> pd.DataFrame:
    """Read one aggregate table; optionally keep one population and drop that column."""
    table = pd.read_parquet(Path(agg_dir) / f"{name}.parquet")
    validate_table(name, table)
    if population is not None and "population" in table.columns:
        table = table.loc[table["population"] == population].drop(columns="population").reset_index(drop=True)
    return table


def read_aggregates(agg_dir: Path) -> tuple[dict[str, pd.DataFrame], dict]:
    """All tables (both populations) plus the manifest."""
    return {name: read_table(agg_dir, name) for name in TABLE_COLUMNS}, read_manifest(agg_dir)
