"""Hand-computed checks for the analysis backend. Run: python -m pytest -q

Fixture (window 2026-09-01..28, horizon 7 days, early = Sep 1-14, last eligible discovery Sep 21):

artist "a" (Alpha)
  u1: Sep 2 (t1, twice), Sep 5 (t2)  -> new, eligible, returned (gap 3 days)
  u2: Sep 3 (t1), Sep 20 (t1)        -> new, eligible, NOT returned (gap 17)
  u3: Aug 15 (t3), Sep 10 (t1)       -> not new (seen before window)
  u4: Sep 25 (t2)                    -> new, NOT eligible (after Sep 21)
artist "b band" ("B Band" / "b band"): u5 (heavy user) Sep 1, u1 Sep 4
"Various Artists": u1 Sep 6 -> excluded from artist metrics
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from analysis import artists, entry, pairs, scoring, segments, trends  # noqa: E402
from analysis.config import AnalysisConfig, ScoringParams  # noqa: E402
from analysis.keys import NON_ARTIST_KEYS, normalize_key  # noqa: E402
from analysis.load import add_listen_day, artist_rows, filter_population  # noqa: E402

CFG = AnalysisConfig()


def listen(row, user, when, artist_name, track, heavy=False):
    return {
        "source_row": row, "user_id": user, "listened_at": pd.Timestamp(when, tz="UTC"),
        "artist_key": normalize_key(artist_name), "artist_name": artist_name,
        "primary_artist_mbid": None, "track_key": normalize_key(track), "track_name": track,
        "flag_heavy_user": heavy, "flag_bad_duration": False, "flag_key_conflict": False,
    }


@pytest.fixture
def listens():
    rows = [
        listen(1, 1, "2026-09-02 10:00", "Alpha", "t1"),
        listen(2, 1, "2026-09-02 11:00", "Alpha", "t1"),
        listen(3, 1, "2026-09-05 09:00", "Alpha", "t2"),
        listen(4, 2, "2026-09-03 12:00", "Alpha", "t1"),
        listen(5, 2, "2026-09-20 12:00", "Alpha", "t1"),
        listen(6, 3, "2026-08-15 08:00", "Alpha", "t3"),
        listen(7, 3, "2026-09-10 08:00", "Alpha", "t1"),
        listen(8, 4, "2026-09-25 20:00", "Alpha", "t2"),
        listen(9, 5, "2026-09-01 07:00", "B Band", "x", heavy=True),
        listen(10, 1, "2026-09-04 07:00", "b band", "y"),
        listen(11, 1, "2026-09-06 07:00", "Various Artists", "z"),
    ]
    return add_listen_day(pd.DataFrame(rows))


def build(listens, population="all", cfg=CFG):
    rows = artist_rows(filter_population(listens, population))
    p = pairs.listener_artist_pairs(rows, cfg)
    return rows, p, artists.artist_metrics(rows, p, cfg)


def test_keys():
    assert normalize_key("  ＢＴＳ ") == "bts"
    assert normalize_key("G  Jones,  Eprom") == "g jones, eprom"
    assert normalize_key("   ") is None
    assert normalize_key("Various Artists") in NON_ARTIST_KEYS


def test_pairs_discovery_and_return(listens):
    _, p, _ = build(listens)
    a = p[p.artist_key == "alpha"].set_index("user_id")
    assert a["discovered_in_window"].to_dict() == {1: True, 2: True, 3: False, 4: True}
    assert a["eligible"].to_dict() == {1: True, 2: True, 3: False, 4: False}
    assert a["returned"].to_dict() == {1: True, 2: False, 3: False, 4: False}
    assert a.loc[1, "window_listens"] == 3 and a.loc[1, "window_active_days"] == 2
    assert a.loc[3, "entry_track_key"] == "t3"  # first-ever listen is in August
    assert "various artists" not in set(p.artist_key)


def test_artist_metrics(listens):
    _, _, m = build(listens)
    a = m.set_index("artist_key").loc["alpha"]
    assert a.window_listens == 7 and a.window_listeners == 4
    assert a.repeat_listener_rate == 0.5
    assert (a.new_listeners, a.eligible_new_listeners, a.returned_new_listeners) == (3, 2, 1)
    assert a.return_rate == 0.5
    assert (a.early_listeners, a.late_listeners) == (3, 2)
    assert a.growth_ratio == pytest.approx(3 / 4)
    assert a.distinct_tracks == 2
    assert a.top_listener_share == pytest.approx(3 / 7)
    assert a.first_seen_day == pd.Timestamp("2026-08-15")
    b = m.set_index("artist_key").loc["b band"]
    assert b.window_listeners == 2 and b.artist_name in {"B Band", "b band"}
    assert b.return_rate == 0.0


def test_population_filter_drops_heavy_user(listens):
    _, _, m = build(listens, "exclude_heavy")
    assert "b band" not in set(m.artist_key)  # 1 listener left, below store_min_listeners=2
    with pytest.raises(ValueError):
        filter_population(listens, "everyone")


def test_weekly(listens):
    rows, p, m = build(listens)
    w = trends.artist_weekly(rows, p, CFG, artist_keys=["alpha"]).set_index("week_index")
    assert w["listens"].tolist() == [4, 1, 1, 1]
    assert w["listeners"].tolist() == [2, 1, 1, 1]
    assert w["new_listeners"].tolist() == [2, 0, 0, 1]
    assert w["days_in_week"].tolist() == [7, 7, 7, 7]


def test_entry_tracks(listens):
    _, p, _ = build(listens)
    e = entry.entry_tracks(p)
    a = e[e.artist_key == "alpha"].set_index("entry_track_key")
    assert a.loc["t1", ["new_listeners", "eligible_new_listeners", "returned_new_listeners"]].tolist() == [2, 2, 1]
    assert a.loc["t1", "return_rate"] == 0.5
    assert a.loc["t2", "new_listeners"] == 1 and math.isnan(a.loc["t2", "return_rate"])
    assert "t3" not in a.index  # u3 is not a new listener


def test_segments(listens):
    cfg = AnalysisConfig(segment_edges=(2, 4))
    rows, p, _ = build(listens, cfg=cfg)
    users = segments.user_segments(rows, cfg).set_index("user_id")["segment"].to_dict()
    assert users == {1: "heavy", 2: "moderate", 3: "light", 4: "light", 5: "light"}
    table = segments.artist_segments(p, segments.user_segments(rows, cfg))
    s = segments.summarize_segments(table, ["alpha"]).set_index("segment")
    assert s.loc["heavy", "returned_new_listeners"] == 1 and s.loc["heavy", "return_rate"] == 1.0
    assert s.loc["moderate", "return_rate"] == 0.0
    assert math.isnan(s.loc["light", "return_rate"])  # u4 not eligible, u3 not new


def metrics_frame():
    return pd.DataFrame({
        "artist_key": ["low", "big", "thin", "c1", "c2", "fan"],
        "window_listeners": [3, 500, 20, 30, 40, 25],
        "eligible_new_listeners": [3, 300, 2, 10, 12, 10],
        "new_listeners": [3, 400, 5, 20, 25, 15],
        "return_rate": [0.5, 0.5, 0.5, 0.2, 0.6, 0.9],
        "repeat_listener_rate": [0.5, 0.5, 0.5, 0.3, 0.5, 0.9],
        "growth_ratio": [1.0, 1.0, 1.0, 1.5, 1.2, 3.0],
        "top_listener_share": [0.1, 0.1, 0.1, 0.1, 0.2, 0.8],
    })


def test_status_and_score():
    s = scoring.score_artists(metrics_frame(), ScoringParams()).set_index("artist_key")
    assert s["status"].to_dict() == {"low": "below_floor", "big": "established", "thin": "insufficient_evidence",
                                     "c1": "candidate", "c2": "candidate", "fan": "candidate"}
    assert s.loc["fan", "single_fan_risk"] and not s.loc["fan", "shortlisted"]
    # Pool = c1, c2. c2 wins new_listeners, return, repeat; c1 wins growth.
    assert s.loc["c2", "exposure_score"] == pytest.approx(0.75 * 100 + 0.25 * 50)
    assert s.loc["c1", "exposure_score"] == pytest.approx(0.75 * 50 + 0.25 * 100)
    assert (s.loc["c2", "rank"], s.loc["c1", "rank"]) == (1, 2)
    assert pd.isna(s.loc["big", "exposure_score"])
    kept = scoring.score_artists(metrics_frame(), ScoringParams(exclude_single_fan=False))
    assert kept.set_index("artist_key").loc["fan", "rank"] == 1
    with pytest.raises(ValueError):
        scoring.score_artists(metrics_frame(), ScoringParams(weights={"new_listeners": 0}))


@pytest.mark.parametrize("weight", [float("nan"), float("inf"), float("-inf")])
def test_normalized_weights_rejects_nonfinite_values(weight):
    with pytest.raises(ValueError, match="weights must be finite"):
        scoring.normalized_weights(ScoringParams(weights={"new_listeners": weight}))


def test_normalized_weights_rejects_nonfinite_total():
    weights = {"new_listeners": 1e308, "return_rate": 1e308}
    with pytest.raises(ValueError, match="weight total must be finite"):
        scoring.normalized_weights(ScoringParams(weights=weights))


def test_normalized_weights_preserves_valid_normalization():
    assert scoring.normalized_weights(ScoringParams()) == {
        name: 0.25 for name in scoring.SCORE_COMPONENTS
    }
    weights = {"new_listeners": 2, "return_rate": 1, "repeat_listener_rate": 1}
    assert scoring.normalized_weights(ScoringParams(weights=weights)) == {
        "new_listeners": 0.5, "return_rate": 0.25,
        "repeat_listener_rate": 0.25, "growth_ratio": 0.0,
    }


@pytest.mark.parametrize("top_n, expected", [
    (None, ["c2", "c1"]), (0, []), (1, ["c2"]), (10, ["c2", "c1"]),
])
def test_shortlist_limits(top_n, expected):
    scored = scoring.score_artists(metrics_frame(), ScoringParams())
    result = scoring.shortlist(scored, top_n=top_n)
    assert result["artist_key"].tolist() == expected
    assert result.columns.tolist() == scored.columns.tolist()


def test_shortlist_rejects_negative_limit():
    scored = scoring.score_artists(metrics_frame(), ScoringParams())
    with pytest.raises(ValueError, match="top_n must be non-negative"):
        scoring.shortlist(scored, top_n=-1)


def test_cleaner_on_repository_sample(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "clean_listens.py"), "--input", str(ROOT / "data_sample.jsonl"),
                    "--output-dir", str(tmp_path)], check=True, cwd=ROOT, capture_output=True)
    checks = pd.read_csv(tmp_path / "record_checks.csv")
    assert checks["matches_expected_values"].all()
    clean = pd.read_csv(tmp_path / "listens_clean.csv")
    assert len(clean) == 100 and clean["track_key"].notna().all()
    assert (clean["artist_key"] == clean["artist_name"].map(normalize_key)).all()


def test_demo_aggregates_contract():
    agg = ROOT / "data" / "demo" / "aggregates"
    if not (agg / "manifest.json").exists():
        pytest.skip("demo aggregates not built")
    from analysis import store
    tables, manifest = store.read_aggregates(agg)
    assert manifest["is_demo"] is True
    assert set(tables["artist_metrics"]["population"]) == {"all", "exclude_heavy"}
    assert json.dumps(manifest)
