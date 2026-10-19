"""Step 2 of the data flow: cleaned CSV -> typed, analysis-ready Parquet.

Reads ``outputs/listens_clean.csv`` (written by clean_listens.py) in chunks,
keeps the columns the analysis needs, sets explicit types, and writes
``data/processed/listens.parquet``. No rows are dropped here: exclusions are
analysis rules applied in ``analysis.load`` so they stay visible and testable.

    python prepare_analysis_data.py
    python prepare_analysis_data.py --input outputs/demo/listens_clean.csv --output data/demo/listens.parquet
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from analysis.config import CLEAN_CSV, LISTENS_PARQUET
from analysis.load import LISTENS_SCHEMA

CHUNK_ROWS = 500_000
BOOL_COLUMNS = ["flag_heavy_user", "flag_bad_duration", "flag_key_conflict"]
TEXT_COLUMNS = ["artist_key", "artist_name", "primary_artist_mbid", "track_key", "track_name"]


def to_bool(series: pd.Series) -> pd.Series:
    """The cleaner writes Python booleans as the text True/False."""
    return series.astype("string").str.strip().str.lower().eq("true").fillna(False).astype(bool)


def prepare_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({
        "source_row": pd.to_numeric(chunk["source_row"], errors="raise").astype("int64"),
        "user_id": pd.to_numeric(chunk["user_id"], errors="raise").astype("int64"),
        "listened_at": pd.to_datetime(chunk["listened_at"], utc=True, errors="raise"),
    })
    for column in TEXT_COLUMNS:
        values = chunk[column].astype("string")
        out[column] = values.where(values.str.len() > 0)
    for column in BOOL_COLUMNS:
        out[column] = to_bool(chunk[column])
    return out[list(LISTENS_SCHEMA.names)]


def prepare(input_path: Path, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    usecols = ["source_row", "user_id", "listened_at", *TEXT_COLUMNS, *BOOL_COLUMNS]
    writer = None
    rows = 0
    try:
        reader = pd.read_csv(input_path, usecols=usecols, dtype=str, keep_default_na=False,
                             chunksize=CHUNK_ROWS, encoding="utf-8")
        for chunk in reader:
            table = pa.Table.from_pandas(prepare_chunk(chunk), schema=LISTENS_SCHEMA, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(output_path, LISTENS_SCHEMA, compression="zstd")
            writer.write_table(table)
            rows += table.num_rows
    finally:
        if writer is not None:
            writer.close()
    if writer is None:  # empty input: still write a valid empty file
        pq.write_table(LISTENS_SCHEMA.empty_table(), output_path)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=CLEAN_CSV)
    parser.add_argument("--output", type=Path, default=LISTENS_PARQUET)
    args = parser.parse_args()
    if not args.input.is_file():
        sys.exit(f"Cleaned CSV not found: {args.input}. Run clean_listens.py first.")
    rows = prepare(args.input, args.output)
    print(f"Wrote {rows:,} rows to {args.output}")


if __name__ == "__main__":
    main()
