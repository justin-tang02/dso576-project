"""Load V3 artist-level metrics and rankings."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
V3_DIR = PROJECT_ROOT / "data/v3"
V2_DIR = PROJECT_ROOT / "data/aggregates"


@dataclass
class Context:
    scored: pd.DataFrame
    metrics: pd.DataFrame
    entry_tracks: pd.DataFrame
    artist_segments: pd.DataFrame
    segment_users: pd.DataFrame


@st.cache_data(show_spinner="Loading V3 artist data...")
def load_data():
    scores_path = V3_DIR / "artist_scores.parquet"
    metrics_path = V3_DIR / "artist_period_metrics.parquet"

    for path in (scores_path, metrics_path):
        if not path.is_file():
            raise FileNotFoundError(f"Missing V3 dataset: {path}")

    scored = pd.read_parquet(scores_path)
    metrics = pd.read_parquet(metrics_path)

    required = {
        "artist_key",
        "artist_name",
        "sep_listeners",
        "oct_listeners",
        "audience_change",
        "audience_growth_pct",
        "retention_rate",
        "oct_depth",
        "oct_top_listener_share",
        "growth_score",
        "retention_score",
        "depth_score",
        "breadth_score",
        "v3_score",
    }

    missing = required - set(scored.columns)
    if missing:
        raise ValueError(f"Missing V3 columns: {sorted(missing)}")

    entry_tracks = pd.read_parquet(
        V2_DIR / "entry_tracks.parquet"
    )
    artist_segments = pd.read_parquet(
        V2_DIR / "artist_segments.parquet"
    )
    segment_users = pd.read_parquet(
        V2_DIR / "segment_users.parquet"
    )

    # V2 aggregates contain both population variants.
    # Use the original all-listener population consistently.
    entry_tracks = entry_tracks.loc[
        entry_tracks.population.eq("all")
    ].copy()
    artist_segments = artist_segments.loc[
        artist_segments.population.eq("all")
    ].copy()
    segment_users = segment_users.loc[
        segment_users.population.eq("all")
    ].copy()

    return Context(
        scored=scored,
        metrics=metrics,
        entry_tracks=entry_tracks,
        artist_segments=artist_segments,
        segment_users=segment_users,
    )
