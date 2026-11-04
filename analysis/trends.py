"""Weekly series per artist for the trend chart.

Week k covers window days [start + 7k, start + 7k + 6]. With the default
28-day window there are exactly four full weeks. ``days_in_week`` marks a
short final week if the window length is not a multiple of 7.
"""

from __future__ import annotations

import pandas as pd

from .config import AnalysisConfig
from .load import window_rows

WEEKLY_COLUMNS = ["artist_key", "week_index", "week_start", "days_in_week",
                  "listens", "listeners", "new_listeners"]


def week_frame(cfg: AnalysisConfig) -> pd.DataFrame:
    start = pd.Timestamp(cfg.window_start)
    n_weeks = -(-cfg.n_days // 7)
    weeks = pd.DataFrame({"week_index": range(n_weeks)})
    weeks["week_start"] = start + pd.to_timedelta(weeks["week_index"] * 7, unit="D")
    weeks["days_in_week"] = [min(7, cfg.n_days - 7 * k) for k in weeks["week_index"]]
    return weeks


def _week_index(days: pd.Series, cfg: AnalysisConfig) -> pd.Series:
    return ((days - pd.Timestamp(cfg.window_start)).dt.days // 7).astype("int64")


def artist_weekly(artist_listens: pd.DataFrame, pairs: pd.DataFrame, cfg: AnalysisConfig,
                  artist_keys: pd.Index | list | None = None) -> pd.DataFrame:
    """Listens, distinct listeners and new listeners per artist per window week.

    Every requested artist gets every week (zeros filled) so charts never skip a week.
    """
    window = window_rows(artist_listens, cfg)
    if artist_keys is not None:
        keys = pd.Index(artist_keys).unique()
        window = window.loc[window["artist_key"].isin(keys)]
        pairs = pairs.loc[pairs["artist_key"].isin(keys)]
    else:
        keys = pd.Index(window["artist_key"].unique())
    if len(keys) == 0:
        return pd.DataFrame(columns=WEEKLY_COLUMNS)

    window = window.assign(week_index=_week_index(window["listen_day"], cfg))
    activity = window.groupby(["artist_key", "week_index"]).agg(
        listens=("user_id", "size"), listeners=("user_id", "nunique"))

    new = pairs.loc[pairs["discovered_in_window"]]
    new = new.assign(week_index=_week_index(new["first_seen_day"], cfg))
    new_counts = new.groupby(["artist_key", "week_index"]).size().rename("new_listeners")

    weeks = week_frame(cfg)
    grid = pd.MultiIndex.from_product([sorted(keys), weeks["week_index"]], names=["artist_key", "week_index"])
    out = (
        pd.concat([activity, new_counts], axis=1).reindex(grid).fillna(0).astype("int64")
        .reset_index().merge(weeks, on="week_index", how="left")
    )
    return out[WEEKLY_COLUMNS]
