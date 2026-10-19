"""Listener activity segments and how each segment engages after discovery.

Segment = a listener's total window listens (artist rows) bucketed by
cfg.segment_edges: light < 50 <= moderate < 500 <= heavy (defaults).
"""

from __future__ import annotations

from typing import Iterable, Optional

import pandas as pd

from .config import SEGMENT_ORDER, AnalysisConfig
from .load import window_rows

USER_SEGMENT_COLUMNS = ["user_id", "window_listens", "segment"]
ARTIST_SEGMENT_COLUMNS = ["artist_key", "segment", "window_listeners", "new_listeners",
                          "eligible_new_listeners", "returned_new_listeners"]
SEGMENT_SUMMARY_COLUMNS = ["segment", "artists", "window_listeners", "new_listeners",
                           "eligible_new_listeners", "returned_new_listeners", "return_rate"]


def segment_for(listens: int, edges: tuple[int, int]) -> str:
    low, high = edges
    if listens < low:
        return "light"
    if listens < high:
        return "moderate"
    return "heavy"


def user_segments(artist_listens: pd.DataFrame, cfg: AnalysisConfig) -> pd.DataFrame:
    """One row per window listener with their activity segment."""
    counts = window_rows(artist_listens, cfg).groupby("user_id").size().rename("window_listens").reset_index()
    counts["segment"] = counts["window_listens"].map(lambda n: segment_for(int(n), cfg.segment_edges))
    counts["window_listens"] = counts["window_listens"].astype("int64")
    return counts[USER_SEGMENT_COLUMNS]


def segment_users_summary(users: pd.DataFrame) -> pd.DataFrame:
    """Users and listens per segment (for the segment view header)."""
    out = users.groupby("segment").agg(users=("user_id", "size"), window_listens=("window_listens", "sum"))
    out = out.reindex(list(SEGMENT_ORDER), fill_value=0).reset_index()
    total = out["window_listens"].sum()
    out["share_of_listens"] = out["window_listens"] / total if total else 0.0
    return out


def artist_segments(pairs: pd.DataFrame, users: pd.DataFrame) -> pd.DataFrame:
    """Per (artist, segment) counts. Rates are computed later so sums stay additive."""
    p = pairs.merge(users[["user_id", "segment"]], on="user_id", how="left", validate="many_to_one")
    p["returned_eligible"] = p["returned"] & p["eligible"]
    out = p.groupby(["artist_key", "segment"]).agg(
        window_listeners=("user_id", "size"),
        new_listeners=("discovered_in_window", "sum"),
        eligible_new_listeners=("eligible", "sum"),
        returned_new_listeners=("returned_eligible", "sum"),
    ).reset_index()
    for col in ARTIST_SEGMENT_COLUMNS[2:]:
        out[col] = out[col].astype("int64")
    return out[ARTIST_SEGMENT_COLUMNS]


def summarize_segments(artist_segment_table: pd.DataFrame,
                       artist_keys: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """Aggregate artist x segment counts over a set of artists (e.g. the live shortlist).

    Cheap enough to call on every dashboard interaction.
    """
    table = artist_segment_table
    if artist_keys is not None:
        table = table.loc[table["artist_key"].isin(set(artist_keys))]
    out = table.groupby("segment").agg(
        artists=("artist_key", "nunique"),
        window_listeners=("window_listeners", "sum"),
        new_listeners=("new_listeners", "sum"),
        eligible_new_listeners=("eligible_new_listeners", "sum"),
        returned_new_listeners=("returned_new_listeners", "sum"),
    ).reindex(list(SEGMENT_ORDER), fill_value=0).reset_index()
    eligible = out["eligible_new_listeners"].where(out["eligible_new_listeners"] > 0)
    out["return_rate"] = (out["returned_new_listeners"] / eligible).astype("float64")
    return out[SEGMENT_SUMMARY_COLUMNS]
