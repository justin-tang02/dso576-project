"""Data coverage facts for the Data Notes view and the sufficiency banner."""

from __future__ import annotations


import pandas as pd

from .config import AnalysisConfig
from .keys import NON_ARTIST_KEYS
from .load import window_rows

# If fewer window listeners than this share were active on 2+ days, return and
# repeat metrics have little to measure and the dashboard shows a warning.
MIN_MULTI_DAY_SHARE = 0.20
DAILY_COVERAGE_DAYS = 60


def daily_coverage(listens: pd.DataFrame, cfg: AnalysisConfig, days: int = DAILY_COVERAGE_DAYS) -> pd.DataFrame:
    """Listens and distinct listeners per UTC day for the ``days`` days ending at window_end."""
    end = pd.Timestamp(cfg.window_end)
    start = end - pd.Timedelta(days=days - 1)
    recent = listens.loc[listens["listen_day"].between(start, end)]
    out = recent.groupby("listen_day").agg(listens=("user_id", "size"), listeners=("user_id", "nunique"))
    out = out.reindex(pd.date_range(start, end, freq="D"), fill_value=0).rename_axis("listen_day").reset_index()
    out["in_window"] = out["listen_day"] >= pd.Timestamp(cfg.window_start)
    return out


def data_quality(listens: pd.DataFrame, cfg: AnalysisConfig, artist_metrics: pd.DataFrame | None = None) -> dict:
    """Headline coverage numbers (JSON-serializable) for all users, before population filters."""
    window = window_rows(listens, cfg)
    n_all, n_win = len(listens), len(window)
    non_artist = window["artist_key"].isna() | window["artist_key"].isin(NON_ARTIST_KEYS)
    active_days = window[["user_id", "listen_day"]].drop_duplicates().groupby("user_id").size()
    multi_day_share = float((active_days >= 2).mean()) if len(active_days) else 0.0
    facts = {
        "window_start": cfg.window_start.isoformat(),
        "window_end": cfg.window_end.isoformat(),
        "first_listen_utc": listens["listened_at"].min().isoformat() if n_all else None,
        "last_listen_utc": listens["listened_at"].max().isoformat() if n_all else None,
        "total_listens": int(n_all),
        "window_listens": int(n_win),
        "window_share": n_win / n_all if n_all else 0.0,
        "window_listeners": int(window["user_id"].nunique()),
        "window_artists": int(window.loc[~non_artist, "artist_key"].nunique()),
        "window_non_artist_listens": int(non_artist.sum()),
        "window_mbid_share": float(window["primary_artist_mbid"].notna().mean()) if n_win else 0.0,
        "window_heavy_user_listen_share": float(window["flag_heavy_user"].mean()) if n_win else 0.0,
        "window_heavy_users": int(window.loc[window["flag_heavy_user"], "user_id"].nunique()),
        "multi_day_listener_share": multi_day_share,
        "retention_sufficient": multi_day_share >= MIN_MULTI_DAY_SHARE,
        "last_eligible_discovery": cfg.last_eligible_discovery.isoformat(),
    }
    if artist_metrics is not None and len(artist_metrics):
        q = artist_metrics["window_listeners"].quantile([0.5, 0.9, 0.99]).to_dict()
        facts["artist_listeners_p50"] = float(q[0.5])
        facts["artist_listeners_p90"] = float(q[0.9])
        facts["artist_listeners_p99"] = float(q[0.99])
        facts["artist_listeners_max"] = int(artist_metrics["window_listeners"].max())
    return facts
