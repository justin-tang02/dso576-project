"""Live scoring: status, shortlist and exposure score from one population's artist metrics.

Pure functions on the ``artist_metrics`` table; fast enough (one pass, a few
rank calls) to rerun on every dashboard control change. Nothing here reads files.
"""

from __future__ import annotations

import math

import pandas as pd

from .config import ScoringParams

STATUS_ORDER = ("candidate", "insufficient_evidence", "established", "below_floor")
SCORE_COMPONENTS = ("new_listeners", "return_rate", "repeat_listener_rate", "growth_ratio")


def assign_status(metrics: pd.DataFrame, params: ScoringParams) -> pd.DataFrame:
    """Add ``status`` and ``single_fan_risk``. Rules are checked in this order:

    below_floor            window_listeners < min_listeners
    established            window_listeners > max_listeners
    insufficient_evidence  eligible_new_listeners < min_eligible_new
    candidate              everything else
    """
    if params.min_listeners > params.max_listeners:
        raise ValueError("min_listeners must not exceed max_listeners")
    out = metrics.copy()
    status = pd.Series("candidate", index=out.index, dtype="object")
    status[out["eligible_new_listeners"] < params.min_eligible_new] = "insufficient_evidence"
    status[out["window_listeners"] > params.max_listeners] = "established"
    status[out["window_listeners"] < params.min_listeners] = "below_floor"
    out["status"] = status
    out["single_fan_risk"] = out["top_listener_share"] > params.single_fan_share
    return out


def normalized_weights(params: ScoringParams) -> dict[str, float]:
    unknown = set(params.weights) - set(SCORE_COMPONENTS)
    if unknown:
        raise ValueError(f"unknown score components: {sorted(unknown)}")
    weights = {name: float(params.weights.get(name, 0.0)) for name in SCORE_COMPONENTS}
    if any(not math.isfinite(w) for w in weights.values()):
        raise ValueError("weights must be finite")
    if any(w < 0 for w in weights.values()):
        raise ValueError("weights must be non-negative")
    total = sum(weights.values())
    if not math.isfinite(total):
        raise ValueError("weight total must be finite")
    if total == 0:
        raise ValueError("at least one weight must be positive")
    return {name: w / total for name, w in weights.items()}


def score_artists(metrics: pd.DataFrame, params: ScoringParams) -> pd.DataFrame:
    """Status, shortlist flag, component percentiles, exposure_score (0-100) and rank.

    Only shortlisted artists (status == candidate, and no single_fan_risk when
    exclude_single_fan is on) get percentiles, a score and a rank; others are NaN.
    Percentiles are ranked within the shortlist, so the score is relative to
    the current filter settings. Ties: score desc, new_listeners desc, artist_key asc.
    """
    out = assign_status(metrics, params)
    shortlisted = out["status"].eq("candidate")
    if params.exclude_single_fan:
        shortlisted &= ~out["single_fan_risk"]
    out["shortlisted"] = shortlisted

    weights = normalized_weights(params)
    pool = out.loc[shortlisted]
    out["exposure_score"] = float("nan")
    for name in SCORE_COMPONENTS:
        out[f"pct_{name}"] = float("nan")
        if len(pool):
            out.loc[pool.index, f"pct_{name}"] = pool[name].rank(pct=True, method="average") * 100
    if len(pool):
        score = sum(out.loc[pool.index, f"pct_{name}"] * w for name, w in weights.items())
        out.loc[pool.index, "exposure_score"] = score.round(1)
        order = out.loc[pool.index].sort_values(
            ["exposure_score", "new_listeners", "artist_key"], ascending=[False, False, True], kind="stable")
        out["rank"] = pd.Series(range(1, len(order) + 1), index=order.index, dtype="Int64")
    else:
        out["rank"] = pd.Series(pd.NA, index=out.index, dtype="Int64")
    return out


def shortlist(scored: pd.DataFrame, top_n: int | None = None) -> pd.DataFrame:
    """Shortlisted rows of ``score_artists`` output, ordered by rank."""
    if top_n is not None and top_n < 0:
        raise ValueError("top_n must be non-negative")
    rows = scored.loc[scored["shortlisted"]].sort_values("rank", kind="stable")
    return rows if top_n is None else rows.head(top_n)


def status_counts(scored: pd.DataFrame) -> pd.DataFrame:
    """Artists per status (for the funnel line under the KPI tiles)."""
    counts = scored["status"].value_counts().reindex(list(STATUS_ORDER), fill_value=0)
    return counts.rename_axis("status").reset_index(name="artists")
