"""Read the analysis-ready listens table and apply the canonical exclusions.

Input contract (data/processed/listens.parquet, one row per cleaned listen):
see LISTENS_SCHEMA. Every function returns a new DataFrame and never mutates
its input.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa

from .config import POPULATIONS, AnalysisConfig
from .keys import NON_ARTIST_KEYS

LISTENS_SCHEMA = pa.schema([
    ("source_row", pa.int64()),
    ("user_id", pa.int64()),
    ("listened_at", pa.timestamp("us", tz="UTC")),
    ("artist_key", pa.string()),
    ("artist_name", pa.string()),
    ("primary_artist_mbid", pa.string()),
    ("track_key", pa.string()),
    ("track_name", pa.string()),
    ("flag_heavy_user", pa.bool_()),
    ("flag_bad_duration", pa.bool_()),
    ("flag_key_conflict", pa.bool_()),
])
REQUIRED_COLUMNS = tuple(LISTENS_SCHEMA.names)


def validate_listens(listens: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in listens.columns]
    if missing:
        raise ValueError(f"listens table is missing columns: {missing}")


def load_listens(path: Path) -> pd.DataFrame:
    """All cleaned listens with a ``listen_day`` (UTC midnight, tz-naive) column added."""
    listens = pd.read_parquet(path, columns=list(REQUIRED_COLUMNS))
    validate_listens(listens)
    return add_listen_day(listens)


def add_listen_day(listens: pd.DataFrame) -> pd.DataFrame:
    out = listens.copy()
    out["listened_at"] = pd.to_datetime(out["listened_at"], utc=True)
    out["listen_day"] = out["listened_at"].dt.tz_convert("UTC").dt.tz_localize(None).dt.floor("D")
    return out


def artist_rows(listens: pd.DataFrame) -> pd.DataFrame:
    """Rows usable for artist metrics: an artist_key that names a real artist."""
    keep = listens["artist_key"].notna() & ~listens["artist_key"].isin(NON_ARTIST_KEYS)
    return listens.loc[keep].copy()


def filter_population(listens: pd.DataFrame, population: str) -> pd.DataFrame:
    """'all' keeps everyone; 'exclude_heavy' drops users flagged by the cleaner."""
    if population not in POPULATIONS:
        raise ValueError(f"population must be one of {POPULATIONS}, got {population!r}")
    if population == "all":
        return listens.copy()
    return listens.loc[~listens["flag_heavy_user"]].copy()


def window_rows(listens: pd.DataFrame, cfg: AnalysisConfig) -> pd.DataFrame:
    """Listens whose UTC day falls inside the analysis window (inclusive)."""
    start = pd.Timestamp(cfg.window_start)
    end = pd.Timestamp(cfg.window_end)
    mask = listens["listen_day"].between(start, end)
    return listens.loc[mask].copy()
