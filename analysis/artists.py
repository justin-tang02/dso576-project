"""One row per artist: reach, engagement, growth and concentration in the window."""

from __future__ import annotations

import pandas as pd

from .config import AnalysisConfig
from .load import window_rows

ARTIST_METRIC_COLUMNS = [
    "artist_key", "artist_name", "primary_artist_mbid", "first_seen_day",
    "window_listens", "window_listeners", "listens_per_listener", "repeat_listener_rate",
    "new_listeners", "eligible_new_listeners", "returned_new_listeners", "return_rate",
    "early_listeners", "late_listeners", "growth_ratio", "distinct_tracks", "top_listener_share",
]


def most_common(frame: pd.DataFrame, key: str, value: str) -> pd.Series:
    """Most frequent non-null ``value`` per ``key``; ties go to the alphabetically first value."""
    present = frame.loc[frame[value].notna(), [key, value]]
    counts = present.groupby([key, value], sort=False).size().rename("n").reset_index()
    counts = counts.sort_values([key, "n", value], ascending=[True, False, True], kind="stable")
    return counts.drop_duplicates(key).set_index(key)[value]


def artist_metrics(artist_listens: pd.DataFrame, pairs: pd.DataFrame, cfg: AnalysisConfig) -> pd.DataFrame:
    """Per-artist metrics for one population.

    ``artist_listens``: artist rows of one population, all history.
    ``pairs``: output of ``pairs.listener_artist_pairs`` for the same rows.
    Artists with fewer than ``cfg.store_min_listeners`` window listeners are dropped.
    """
    window = window_rows(artist_listens, cfg)
    if window.empty or pairs.empty:
        return pd.DataFrame(columns=ARTIST_METRIC_COLUMNS)

    p = pairs.assign(
        repeat=pairs["window_active_days"] >= 2,
        returned_eligible=pairs["returned"] & pairs["eligible"],
    )
    by_artist = p.groupby("artist_key", sort=True).agg(
        window_listens=("window_listens", "sum"),
        window_listeners=("user_id", "size"),
        repeaters=("repeat", "sum"),
        new_listeners=("discovered_in_window", "sum"),
        eligible_new_listeners=("eligible", "sum"),
        returned_new_listeners=("returned_eligible", "sum"),
        early_listeners=("in_early", "sum"),
        late_listeners=("in_late", "sum"),
        top_listener_listens=("window_listens", "max"),
    )
    out = by_artist.reset_index()
    out = out.loc[out["window_listeners"] >= cfg.store_min_listeners].copy()

    out["listens_per_listener"] = out["window_listens"] / out["window_listeners"]
    out["repeat_listener_rate"] = out["repeaters"] / out["window_listeners"]
    # NaN (not 0) when no new listener had a full return horizon.
    eligible = out["eligible_new_listeners"].where(out["eligible_new_listeners"] > 0)
    out["return_rate"] = (out["returned_new_listeners"] / eligible).astype("float64")
    out["growth_ratio"] = (out["late_listeners"] + 1) / (out["early_listeners"] + 1)
    out["top_listener_share"] = out["top_listener_listens"] / out["window_listens"]

    tracks = window.groupby("artist_key")["track_key"].nunique().rename("distinct_tracks")
    first_seen = artist_listens.groupby("artist_key")["listen_day"].min().rename("first_seen_day")
    out = (
        out.merge(tracks, left_on="artist_key", right_index=True, how="left")
        .merge(first_seen, left_on="artist_key", right_index=True, how="left")
    )
    out["artist_name"] = out["artist_key"].map(most_common(window, "artist_key", "artist_name"))
    out["primary_artist_mbid"] = out["artist_key"].map(most_common(window, "artist_key", "primary_artist_mbid"))

    int_cols = ["window_listens", "window_listeners", "new_listeners", "eligible_new_listeners",
                "returned_new_listeners", "early_listeners", "late_listeners", "distinct_tracks"]
    out[int_cols] = out[int_cols].fillna(0).astype("int64")
    return out[ARTIST_METRIC_COLUMNS].reset_index(drop=True)
