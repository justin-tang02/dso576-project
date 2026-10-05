import csv
import contextlib
import hashlib
import json
import sqlite3
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

input_file = Path("9.listens")
output_file = Path("cleaned_sample.csv")

relevant_cols = [
    "user_id",
    "user_name",
    "timestamp",
    "recording_msid",
    "track_metadata.track_name",
    "track_metadata.artist_name",
    "track_metadata.release_name",
]
text_cols = [
    "user_name",
    "track_metadata.track_name",
    "track_metadata.artist_name",
    "track_metadata.release_name",
]

missing_counts = {column: 0 for column in relevant_cols}
failed_timestamps = 0
blank_artists = 0
blank_tracks = 0
future_dates = 0
starting_rows = 0
exact_duplicates = 0
repeated_recording_msids = 0

sample_rows = []
sample_cases = set()
sample_candidates = []
normal_candidates = []

with tempfile.TemporaryDirectory(prefix="clean-listens-") as temp_dir:
    with contextlib.closing(
        sqlite3.connect(Path(temp_dir) / "duplicates.sqlite3")
    ) as database:
        database.execute("CREATE TABLE exact_records (digest BLOB PRIMARY KEY)")
        database.execute("CREATE TABLE recording_ids (digest BLOB PRIMARY KEY)")
        with input_file.open(encoding="utf-8") as infile:
            for line in infile:
                record = json.loads(line)
                starting_rows += 1

                metadata = record.get("track_metadata") or {}
                row = {
                    "user_id": record.get("user_id"),
                    "user_name": record.get("user_name"),
                    "timestamp": record.get("timestamp"),
                    "recording_msid": record.get("recording_msid"),
                    "track_metadata.track_name": metadata.get("track_name"),
                    "track_metadata.artist_name": metadata.get("artist_name"),
                    "track_metadata.release_name": metadata.get("release_name"),
                }

                for column in text_cols:
                    value = row[column]
                    if isinstance(value, str):
                        row[column] = value.strip()

                for column in relevant_cols:
                    if row[column] is None:
                        missing_counts[column] += 1

                try:
                    listen_datetime = datetime.fromtimestamp(
                        float(row["timestamp"]), tz=timezone.utc
                    )
                except (TypeError, ValueError, OverflowError, OSError):
                    listen_datetime = None

                if listen_datetime is None:
                    failed_timestamps += 1
                    listen_datetime_text = ""
                else:
                    listen_datetime_text = listen_datetime.isoformat()
                    if listen_datetime.date() > date(2026, 9, 29):
                        future_dates += 1

                if row["track_metadata.artist_name"] == "":
                    blank_artists += 1
                if row["track_metadata.track_name"] == "":
                    blank_tracks += 1

                # Canonical JSON gives the same hash when object key order differs.
                canonical_record = json.dumps(
                    record, sort_keys=True, ensure_ascii=False, separators=(",", ":")
                )
                record_hash = hashlib.blake2b(
                    canonical_record.encode("utf-8"), digest_size=16
                ).digest()
                inserted = database.execute(
                    "INSERT OR IGNORE INTO exact_records(digest) VALUES (?)",
                    (record_hash,),
                ).rowcount
                if not inserted:
                    exact_duplicates += 1

                recording_id = row["recording_msid"]
                if recording_id is None:
                    repeated_id = False
                else:
                    recording_id_hash = hashlib.blake2b(
                        str(recording_id).encode("utf-8"), digest_size=8
                    ).digest()
                    inserted = database.execute(
                        "INSERT OR IGNORE INTO recording_ids(digest) VALUES (?)",
                        (recording_id_hash,),
                    ).rowcount
                    repeated_id = not inserted
                    if repeated_id:
                        repeated_recording_msids += 1

                # Keep a small pool so difficult cases can be included even if they occur later.
                cleaned_row = {**row, "listen_datetime": listen_datetime_text}
                if len(sample_candidates) < 50:
                    sample_candidates.append((starting_rows, cleaned_row))

                # Save one example of each useful review case.
                missing_release = row["track_metadata.release_name"] is None
                has_unicode = any(
                    isinstance(row[column], str)
                    and any(ord(character) > 127 for character in row[column])
                    for column in text_cols
                )
                cases = []
                if missing_release:
                    cases.append("missing release")
                if repeated_id:
                    cases.append("repeated recording_msid")
                if has_unicode:
                    cases.append("Unicode text")

                if not cases and len(normal_candidates) < 50:
                    normal_candidates.append((starting_rows, cleaned_row))

                if cases and any(case not in sample_cases for case in cases):
                    sample_rows.append((starting_rows, cleaned_row))
                    sample_cases.update(cases)

    selected_indices = {index for index, row in sample_rows}
    for candidates in (normal_candidates, sample_candidates):
        for index, row in candidates:
            if len(sample_rows) >= 50:
                break
            if index not in selected_indices:
                sample_rows.append((index, row))
                selected_indices.add(index)
        if len(sample_rows) >= 50:
            break

    sample_rows = [row for index, row in sample_rows]
    final_rows = starting_rows

    output_cols = relevant_cols + ["listen_datetime"]
    with output_file.open("w", encoding="utf-8-sig", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=output_cols)
        writer.writeheader()
        writer.writerows(sample_rows)

    print("Total starting rows:", starting_rows)
    print("Total final rows:", final_rows)
    print("Missing values by relevant field:")
    for column, count in missing_counts.items():
        print(f"  {column}: {count}")
    print("Failed timestamp conversions:", failed_timestamps)
    print("Blank artist names:", blank_artists)
    print("Blank track names:", blank_tracks)
    print("Listening dates after September 29, 2026:", future_dates)
    print("Repeated recording_msid values:", repeated_recording_msids)
    print("Exact duplicate listening-event rows:", exact_duplicates)
    print("Sample CSV:", output_file.name)
    print("Sample rows written:", len(sample_rows))
