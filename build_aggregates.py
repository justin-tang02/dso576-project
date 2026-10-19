"""Step 3 of the data flow: analysis-ready listens -> dashboard aggregate files.

    python build_aggregates.py
    python build_aggregates.py --listens data/demo/listens.parquet --out data/demo/aggregates --demo

Writes the tables in analysis.store.TABLE_COLUMNS plus manifest.json. Each
table (except daily_coverage) has one block of rows per population
("all", "exclude_heavy") so the dashboard toggle never recomputes anything heavy.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from analysis import artists, entry, pairs, quality, segments, store, trends
from analysis.config import AGGREGATES_DIR, LISTENS_PARQUET, POPULATIONS, AnalysisConfig, ScoringParams
from analysis.load import artist_rows, filter_population, load_listens


def build_population(listens: pd.DataFrame, population: str, cfg: AnalysisConfig) -> dict[str, pd.DataFrame]:
    rows = artist_rows(filter_population(listens, population))
    pair_table = pairs.listener_artist_pairs(rows, cfg)
    metrics = artists.artist_metrics(rows, pair_table, cfg)
    stored = metrics["artist_key"]
    kept_pairs = pair_table.loc[pair_table["artist_key"].isin(set(stored))]
    users = segments.user_segments(rows, cfg)
    tables = {
        "artist_metrics": metrics,
        "artist_weekly": trends.artist_weekly(rows, kept_pairs, cfg, artist_keys=stored),
        "entry_tracks": entry.entry_tracks(kept_pairs),
        "artist_segments": segments.artist_segments(kept_pairs, users),
        "segment_users": segments.segment_users_summary(users),
    }
    return {name: t.assign(population=population) for name, t in tables.items()}


def build(listens_path: Path, out_dir: Path, cfg: AnalysisConfig, demo: bool = False) -> dict:
    started = time.time()
    listens = load_listens(listens_path)
    per_pop = {pop: build_population(listens, pop, cfg) for pop in POPULATIONS}
    tables = {name: pd.concat([per_pop[p][name] for p in POPULATIONS], ignore_index=True)
              for name in per_pop[POPULATIONS[0]]}
    tables["daily_coverage"] = quality.daily_coverage(listens, cfg)
    all_metrics = per_pop["all"]["artist_metrics"]
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_listens": str(listens_path),
        "is_demo": demo,
        "analysis_config": {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in asdict(cfg).items()},
        "default_scoring": asdict(ScoringParams()),
        "data_quality": quality.data_quality(listens, cfg, all_metrics),
        "row_counts": {name: int(len(t)) for name, t in tables.items()},
        "build_seconds": round(time.time() - started, 1),
    }
    store.write_aggregates(tables, manifest, out_dir)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--listens", type=Path, default=LISTENS_PARQUET)
    parser.add_argument("--out", type=Path, default=AGGREGATES_DIR)
    parser.add_argument("--demo", action="store_true", help="Mark the output as synthetic demo data")
    args = parser.parse_args()
    if not args.listens.is_file():
        sys.exit(f"Listens table not found: {args.listens}. Run prepare_analysis_data.py first.")
    manifest = build(args.listens, args.out, AnalysisConfig(), demo=args.demo)
    print(f"Wrote aggregates to {args.out} in {manifest['build_seconds']}s")
    for name, count in manifest["row_counts"].items():
        print(f"  {name}: {count:,} rows")


if __name__ == "__main__":
    main()
