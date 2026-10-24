"""One row per (listener, artist) pair active in the window.

This is the building block for every engagement metric. Definitions
(BUILD_SPEC.md "Metric definitions"):

* first_seen_day: the pair's earliest listen in all cleaned history (not just the window).
* discovered_in_window: first_seen_day is inside the window ("new listener").
* eligible: discovered on or before cfg.last_eligible_discovery, so a full
  return horizon is observable inside the window.
* returned: eligible and the listener played the artist again on a later day
  within return_horizon_days of first_seen_day.
"""

from __future__ import annotations

import pandas as pd

from .config import AnalysisConfig
from .load import window_rows

PAIR_KEYS = ["user_id", "artist_key"]
PAIR_COLUMNS = [
    "user_id", "artist_key", "first_seen_day", "entry_track_key", "entry_track_name",
    "window_listens", "window_active_days", "in_early", "in_late",
    "discovered_in_window", "eligible", "returned",
]


def listener_artist_pairs(artist_listens: pd.DataFrame, cfg: AnalysisConfig) -> pd.DataFrame:
    """Build the pair table from artist rows of one population (all history).

    ``artist_listens`` must already be population-filtered and passed through
    ``load.artist_rows``; it must contain ``listen_day``.
    """
    ordered = artist_listens.sort_values(["listened_at", "source_row"], kind="stable")
    first = (
        ordered.drop_duplicates(PAIR_KEYS, keep="first")
        [PAIR_KEYS + ["listen_day", "track_key", "track_name"]]
        .rename(columns={"listen_day": "first_seen_day", "track_key": "entry_track_key",
                         "track_name": "entry_track_name"})
    )

    window = window_rows(artist_listens, cfg)
    if window.empty:
        return pd.DataFrame(columns=PAIR_COLUMNS)

    listens_per_pair = window.groupby(PAIR_KEYS, sort=False).size().rename("window_listens")
    days = window[PAIR_KEYS + ["listen_day"]].drop_duplicates()
    late_start = pd.Timestamp(cfg.late_start)
    days["is_early"] = days["listen_day"] < late_start
    day_stats = days.groupby(PAIR_KEYS, sort=False).agg(
        window_active_days=("listen_day", "size"),
        in_early=("is_early", "any"),
        n_early=("is_early", "sum"),
    )
    day_stats["in_late"] = day_stats["window_active_days"] > day_stats["n_early"]
    pairs = (
        pd.concat([listens_per_pair, day_stats.drop(columns="n_early")], axis=1)
        .reset_index()
        .merge(first, on=PAIR_KEYS, how="left", validate="one_to_one")
    )

    start, end = pd.Timestamp(cfg.window_start), pd.Timestamp(cfg.window_end)
    pairs["discovered_in_window"] = pairs["first_seen_day"].between(start, end)
    pairs["eligible"] = pairs["discovered_in_window"] & (
        pairs["first_seen_day"] <= pd.Timestamp(cfg.last_eligible_discovery)
    )

    eligible = pairs.loc[pairs["eligible"], PAIR_KEYS + ["first_seen_day"]]
    follow = days.merge(eligible, on=PAIR_KEYS, how="inner")
    gap = (follow["listen_day"] - follow["first_seen_day"]).dt.days
    returned_keys = follow.loc[(gap >= 1) & (gap <= cfg.return_horizon_days), PAIR_KEYS].drop_duplicates()
    returned_keys["returned"] = True
    pairs = pairs.merge(returned_keys, on=PAIR_KEYS, how="left", validate="one_to_one")
    pairs["returned"] = pairs["returned"].astype("boolean").fillna(False).astype(bool)

    pairs["window_listens"] = pairs["window_listens"].astype("int64")
    pairs["window_active_days"] = pairs["window_active_days"].astype("int64")
    return pairs[PAIR_COLUMNS].sort_values(PAIR_KEYS, kind="stable").reset_index(drop=True)
