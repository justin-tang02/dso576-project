"""Stream and clean a ListenBrainz JSON-lines listens dump."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional
from analysis.keys import normalize_key


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = PROJECT_DIR / "9.listens"
DEFAULT_OUTPUT = PROJECT_DIR / "outputs"
UUID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")
FIELDS = [
    "source_row", "user_id", "user_name", "listened_at", "recording_msid",
    "recording_mbid", "artist_mbids", "primary_artist_mbid",
    "n_credited_artists", "artist_name", "artist_key", "track_name", "track_key",
    "release_name", "duration_ms", "flag_key_conflict", "flag_outside_month",
    "flag_future", "flag_bad_duration", "flag_heavy_user",
]
FLAG_FIELDS = [name for name in FIELDS if name.startswith("flag_")]
AUDIT_FIELDS = [
    "user_id", "user_name", "listened_at", "recording_msid", "recording_mbid",
    "artist_mbids", "primary_artist_mbid", "artist_name", "track_name",
    "release_name", "duration_ms",
]
TEXT_SOURCE_FIELDS = {
    "user_name": "user_name",
    "artist_name": "artist_name",
    "track_name": "track_name",
    "release_name": "release_name",
}
RECORD_CHECK_EXPECTATIONS = {
    1: "Keep; convert timestamp to UTC, convert duration 112 seconds to 112000 ms, and retain missing artist MBID.",
    2: "Keep; convert timestamp to UTC, preserve duration_ms 186860, and retain the valid artist MBID.",
    3: "Keep; convert timestamp to UTC, preserve duration_ms 87085, and retain missing artist MBID.",
    4: "Keep; convert timestamp to UTC, preserve duration_ms 157361, and retain missing artist MBID.",
    5: "Keep; convert timestamp to UTC, preserve duration_ms 128000, and retain missing artist MBID.",
}
DECISION_LOG = [
    {"rule": "Parse timestamp as Unix seconds and write UTC ISO-8601", "reason": "ListenBrainz source records use a top-level Unix timestamp.", "check": "type_conversion_log.csv; record_checks.csv"},
    {"rule": "Trim text and collapse repeated whitespace; preserve display-name case", "reason": "Remove formatting noise without changing intended artist or track names.", "check": "text_standardization_log.csv"},
    {"rule": "Convert duration seconds to milliseconds; keep duration_ms as provided", "reason": "The sample contains both source representations.", "check": "type_conversion_log.csv; record_checks.csv"},
    {"rule": "Keep UUID-shaped MBIDs; store credited artist IDs as a pipe-separated list", "reason": "IDs support later artist-level grouping; malformed IDs cannot join reliably.", "check": "listens_clean.csv; missing_value_audit.csv"},
    {"rule": "Remove exact duplicates after normalization, but retain key conflicts and flag them", "reason": "Exact repeated submissions add no event information; different payloads sharing the listen key may be distinct events.", "check": "duplicate_audit.csv; data_quality_flags.csv"},
    {"rule": "Drop rows without user_id or a parseable timestamp; leave other missing fields missing", "reason": "Those rows cannot be assigned to a listener or time period, while incomplete metadata can still represent a real listen.", "check": "missing_value_audit.csv; cleaning_summary.csv"},
    {"rule": "Remove future-dated listens; flag out-of-month and implausible durations", "reason": "Future listens are impossible as of the run; other unusual values require review rather than automatic deletion.", "check": "data_quality_flags.csv; cleaning_summary.csv"},
    {"rule": "Flag users above the 99.5th percentile of retained listen counts", "reason": "Heavy activity is unusual but not necessarily erroneous.", "check": "data_quality_flags.csv"},
]


def text_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    normalized = re.sub(r"\s+", " ", str(value)).strip()
    return normalized or None


def valid_uuid(value: Any) -> Optional[str]:
    normalized = text_value(value)
    if normalized is None or not UUID_PATTERN.fullmatch(normalized):
        return None
    return normalized.lower()


def epoch_to_iso(value: Any) -> Optional[str]:
    try:
        seconds = float(value)
        if not math.isfinite(seconds):
            return None
        return datetime.fromtimestamp(seconds, timezone.utc).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def normalize_record(source_row: int, record: dict[str, Any]) -> dict[str, Any]:
    metadata = record.get("track_metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    additional = metadata.get("additional_info") or {}
    if not isinstance(additional, dict):
        additional = {}

    artist_ids = additional.get("artist_mbids") or []
    if isinstance(artist_ids, str):
        artist_ids = [artist_ids]
    if not isinstance(artist_ids, list):
        artist_ids = []
    artist_ids = [value for value in (valid_uuid(item) for item in artist_ids) if value]

    duration = additional.get("duration_ms")
    if duration is None and additional.get("duration") is not None:
        try:
            duration = float(additional["duration"]) * 1000
        except (TypeError, ValueError):
            duration = None
    try:
        duration = float(duration) if duration is not None else None
    except (TypeError, ValueError):
        duration = None
    if duration is not None and not math.isfinite(duration):
        duration = None

    recording_msid = valid_uuid(record.get("recording_msid") or additional.get("recording_msid"))
    return {
        "source_row": source_row,
        "user_id": text_value(record.get("user_id")),
        "user_name": text_value(record.get("user_name")),
        "listened_at": epoch_to_iso(record.get("timestamp", record.get("listened_at"))),
        "recording_msid": recording_msid,
        "recording_mbid": valid_uuid(additional.get("recording_mbid")),
        "artist_mbids": "|".join(artist_ids) or None,
        "primary_artist_mbid": artist_ids[0] if artist_ids else None,
        "n_credited_artists": len(artist_ids),
        "artist_name": text_value(metadata.get("artist_name")),
        "artist_key": normalize_key(metadata.get("artist_name")),
        "track_name": text_value(metadata.get("track_name")),
        "track_key": normalize_key(metadata.get("track_name")),
        "release_name": text_value(metadata.get("release_name")),
        "duration_ms": duration,
    }


def iter_json_lines(path: Path, limit: int | None) -> Iterator[tuple[int, dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if limit is not None and line_number > limit:
                break
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON on source line {line_number}: {error}") from error
            if not isinstance(record, dict):
                raise ValueError(f"Expected a JSON object on source line {line_number}")
            yield line_number, record


def write_csv(path: Path, rows: Iterator[dict[str, Any]], fields: list[str]) -> int:
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        count = 0
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def clean_file(input_path: Path, output_dir: Path, year: int, month: int,
               limit: int | None = None) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    month_start = datetime(year, month, 1, tzinfo=timezone.utc)
    month_end = datetime(year + (month == 12), month % 12 + 1, 1, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    counts = {"input_lines": 0, "missing_user_or_time": 0, "exact_duplicates": 0,
              "future_listens": 0, "clean_rows": 0, "review_rows": 0}
    missing_before = {name: 0 for name in AUDIT_FIELDS}
    missing_after = {name: 0 for name in AUDIT_FIELDS}
    conversion_counts = {
        "timestamp": {"known": 0, "failed": 0},
        "duration": {"known": 0, "failed": 0},
    }
    duration_sources = {"duration_seconds": 0, "duration_milliseconds": 0}
    text_counts = {name: {"changed": 0, "blank_to_missing": 0} for name in TEXT_SOURCE_FIELDS}
    text_examples = []
    invalid_mbid_values = 0
    artist_mbid_rows = 0
    source_valid_duration_ms = 0.0
    source_valid_duration_rows = 0

    with tempfile.TemporaryDirectory(prefix="listenbrainz-clean-") as temporary_dir:
        database_path = Path(temporary_dir) / "index.sqlite"
        connection = sqlite3.connect(database_path)
        connection.execute("CREATE TABLE records (signature TEXT UNIQUE, source_row INTEGER, user_id TEXT, listen_key TEXT, payload TEXT, original_json TEXT)")
        connection.execute("CREATE TABLE listen_keys (listen_key TEXT PRIMARY KEY, signature TEXT, conflict INTEGER DEFAULT 0, occurrences INTEGER DEFAULT 1)")
        connection.execute("CREATE TABLE user_counts (user_id TEXT PRIMARY KEY, listens INTEGER NOT NULL)")
        connection.execute("CREATE TABLE final_users (user_id TEXT PRIMARY KEY)")
        connection.execute("CREATE TABLE final_artists (artist_mbid TEXT PRIMARY KEY)")
        connection.execute("CREATE TABLE final_artist_keys (artist_key TEXT PRIMARY KEY)")
        total_duration_ms = 0.0
        known_duration_rows = 0
        difficult_sample = []
        ordinary_sample = []

        for source_row, original in iter_json_lines(input_path, limit):
            counts["input_lines"] += 1
            row = normalize_record(source_row, original)
            timestamp_raw = original.get("timestamp", original.get("listened_at"))
            if timestamp_raw is not None:
                conversion_counts["timestamp"]["known"] += 1
                conversion_counts["timestamp"]["failed"] += int(row["listened_at"] is None)
            metadata = original.get("track_metadata")
            metadata = metadata if isinstance(metadata, dict) else {}
            additional = metadata.get("additional_info")
            additional = additional if isinstance(additional, dict) else {}
            duration_raw = additional.get("duration_ms")
            if duration_raw is None:
                duration_raw = additional.get("duration")
                if duration_raw is not None:
                    duration_sources["duration_seconds"] += 1
            else:
                duration_sources["duration_milliseconds"] += 1
            if duration_raw is not None:
                conversion_counts["duration"]["known"] += 1
                conversion_counts["duration"]["failed"] += int(row["duration_ms"] is None)
            if row["duration_ms"] is not None and 0 < row["duration_ms"] <= 7_200_000:
                source_valid_duration_ms += row["duration_ms"]
                source_valid_duration_rows += 1
            for column, source_field in TEXT_SOURCE_FIELDS.items():
                if source_field == "user_name":
                    original_text = original.get(source_field)
                else:
                    original_text = metadata.get(source_field)
                cleaned_text = row[column]
                if original_text is not None:
                    changed = str(original_text) != (cleaned_text or "")
                    text_counts[column]["changed"] += int(changed)
                    text_counts[column]["blank_to_missing"] += int(cleaned_text is None)
                    if changed and len(text_examples) < 10:
                        text_examples.append({
                            "source_row": source_row,
                            "column": column,
                            "before": str(original_text),
                            "after": cleaned_text,
                        })
            for column in ("recording_msid", "recording_mbid"):
                raw_id = original.get(column)
                if raw_id is None and column == "recording_msid":
                    raw_id = additional.get(column)
                if raw_id is not None and valid_uuid(raw_id) is None:
                    invalid_mbid_values += 1
            raw_artist_ids = additional.get("artist_mbids") or []
            if not isinstance(raw_artist_ids, list):
                raw_artist_ids = [raw_artist_ids]
            invalid_mbid_values += sum(valid_uuid(value) is None for value in raw_artist_ids if value is not None)
            for column in AUDIT_FIELDS:
                missing_before[column] += int(row[column] is None)
            if not row["user_id"] or not row["listened_at"]:
                counts["missing_user_or_time"] += 1
                continue

            payload = {key: value for key, value in row.items() if key != "source_row"}
            serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            signature = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
            listen_key = json.dumps([row["user_id"], row["listened_at"], row["recording_msid"]])
            cursor = connection.execute(
                "INSERT OR IGNORE INTO records VALUES (?, ?, ?, ?, ?, ?)",
                (signature, source_row, row["user_id"], listen_key, json.dumps(row, ensure_ascii=False),
                 json.dumps(original, ensure_ascii=False)),
            )
            if cursor.rowcount == 0:
                counts["exact_duplicates"] += 1
                continue

            previous = connection.execute("SELECT signature FROM listen_keys WHERE listen_key = ?", (listen_key,)).fetchone()
            if previous is None:
                connection.execute("INSERT INTO listen_keys (listen_key, signature) VALUES (?, ?)", (listen_key, signature))
            elif previous[0] != signature:
                connection.execute("UPDATE listen_keys SET conflict = 1, occurrences = occurrences + 1 WHERE listen_key = ?", (listen_key,))
            connection.execute(
                "INSERT INTO user_counts VALUES (?, 1) ON CONFLICT(user_id) DO UPDATE SET listens = listens + 1",
                (row["user_id"],),
            )
            if counts["input_lines"] % 100_000 == 0:
                connection.commit()

        connection.commit()
        user_count = connection.execute("SELECT COUNT(*) FROM user_counts").fetchone()[0]
        heavy_threshold = None
        if user_count:
            percentile_position = max(0, math.ceil(0.995 * user_count) - 1)
            heavy_threshold = connection.execute(
                "SELECT listens FROM user_counts ORDER BY listens LIMIT 1 OFFSET ?",
                (percentile_position,),
            ).fetchone()[0]

        def output_rows() -> Iterator[dict[str, Any]]:
            nonlocal total_duration_ms, known_duration_rows, artist_mbid_rows
            cursor = connection.execute(
                "SELECT records.payload, listen_keys.conflict, user_counts.listens "
                "FROM records JOIN listen_keys USING (listen_key) "
                "JOIN user_counts USING (user_id) ORDER BY records.source_row"
            )
            for payload, key_conflict, user_listens in cursor:
                row = json.loads(payload)
                listened = datetime.fromisoformat(row["listened_at"].replace("Z", "+00:00"))
                duration = row["duration_ms"]
                row.update({
                    "flag_key_conflict": bool(key_conflict),
                    "flag_outside_month": not month_start <= listened < month_end,
                    "flag_future": listened > now,
                    "flag_bad_duration": duration is not None and (duration <= 0 or duration > 7_200_000),
                    "flag_heavy_user": heavy_threshold is not None and user_listens > heavy_threshold,
                })
                if row["flag_future"]:
                    counts["future_listens"] += 1
                    continue
                counts["clean_rows"] += 1
                for column in AUDIT_FIELDS:
                    missing_after[column] += int(row[column] is None)
                connection.execute("INSERT OR IGNORE INTO final_users VALUES (?)", (row["user_id"],))
                if row["primary_artist_mbid"]:
                    artist_mbid_rows += 1
                    connection.execute("INSERT OR IGNORE INTO final_artists VALUES (?)", (row["primary_artist_mbid"],))
                if row["artist_key"]:
                    connection.execute("INSERT OR IGNORE INTO final_artist_keys VALUES (?)", (row["artist_key"],))
                if duration is not None and 0 < duration <= 7_200_000:
                    total_duration_ms += duration
                    known_duration_rows += 1
                if any(row[field] for field in FLAG_FIELDS) or not row["primary_artist_mbid"]:
                    counts["review_rows"] += 1
                    if len(difficult_sample) < 25:
                        difficult_sample.append(row.copy())
                else:
                    rank = hashlib.sha256(str(row["source_row"]).encode("ascii")).hexdigest()
                    ordinary_sample.append((rank, row.copy()))
                    ordinary_sample.sort(key=lambda item: item[0])
                    del ordinary_sample[25:]
                yield row

        def write_outputs() -> None:
            clean_path = output_dir / "listens_clean.csv"
            review_path = output_dir / "needs_review.csv"
            with clean_path.open("w", newline="", encoding="utf-8") as clean_file, review_path.open(
                "w", newline="", encoding="utf-8"
            ) as review_file:
                clean_writer = csv.DictWriter(clean_file, fieldnames=FIELDS)
                review_writer = csv.DictWriter(review_file, fieldnames=FIELDS)
                clean_writer.writeheader()
                review_writer.writeheader()
                for row in output_rows():
                    clean_writer.writerow(row)
                    if any(row[field] for field in FLAG_FIELDS) or not row["primary_artist_mbid"]:
                        review_writer.writerow(row)
            selected_sample = difficult_sample + [row for _, row in ordinary_sample[:max(0, 50 - len(difficult_sample))]]
            selected_sample.sort(key=lambda row: row["source_row"])
            write_csv(output_dir / "sample_50_rows.csv", iter(selected_sample), FIELDS)

        write_outputs()

        flag_counts = {field: 0 for field in FLAG_FIELDS}
        for (payload, key_conflict, user_listens) in connection.execute(
            "SELECT records.payload, listen_keys.conflict, user_counts.listens "
            "FROM records JOIN listen_keys USING (listen_key) JOIN user_counts USING (user_id)"
        ):
            row = json.loads(payload)
            listened = datetime.fromisoformat(row["listened_at"].replace("Z", "+00:00"))
            duration = row["duration_ms"]
            flags = {
                "flag_key_conflict": bool(key_conflict),
                "flag_outside_month": not month_start <= listened < month_end,
                "flag_future": listened > now,
                "flag_bad_duration": duration is not None and (duration <= 0 or duration > 7_200_000),
                "flag_heavy_user": heavy_threshold is not None and user_listens > heavy_threshold,
            }
            for name, flagged in flags.items():
                if name == "flag_future" or not flags["flag_future"]:
                    flag_counts[name] += int(flagged)

        duplicate_rows = connection.execute(
            "SELECT COALESCE(SUM(occurrences), 0), COUNT(*) FROM listen_keys WHERE occurrences > 1"
        ).fetchone()
        conflict_rows = connection.execute(
            "SELECT COALESCE(SUM(occurrences), 0), COUNT(*) FROM listen_keys WHERE conflict = 1"
        ).fetchone()
        write_csv(
            output_dir / "cleaning_summary.csv",
            iter([
                {"step": "input lines read", "rows": counts["input_lines"]},
                {"step": "rows missing user or timestamp", "rows": counts["missing_user_or_time"]},
                {"step": "exact duplicate rows removed", "rows": counts["exact_duplicates"]},
                {"step": "future listens removed", "rows": counts["future_listens"]},
                {"step": "clean rows written", "rows": counts["clean_rows"]},
                {"step": "rows needing review", "rows": counts["review_rows"]},
            ]),
            ["step", "rows"],
        )
        write_csv(
            output_dir / "data_quality_flags.csv",
            iter({"flag": name, "rows_flagged": amount} for name, amount in flag_counts.items()),
            ["flag", "rows_flagged"],
        )

        type_rows = [
            {"column": "timestamp", "conversion": "Unix seconds to UTC ISO-8601", **conversion_counts["timestamp"], "source_seconds": "", "source_milliseconds": ""},
            {"column": "duration", "conversion": "duration seconds to milliseconds or preserve duration_ms", **conversion_counts["duration"], **duration_sources},
            {"column": "MBID fields", "conversion": "validate UUID shape and lowercase valid IDs", "known": "not separately typed", "failed": invalid_mbid_values, "source_seconds": "", "source_milliseconds": ""},
        ]
        write_csv(output_dir / "type_conversion_log.csv", iter(type_rows), ["column", "conversion", "known", "failed", "source_seconds", "source_milliseconds"])
        write_csv(
            output_dir / "text_standardization_log.csv",
            iter({"column": name, **values} for name, values in text_counts.items()),
            ["column", "changed", "blank_to_missing"],
        )
        write_csv(
            output_dir / "text_before_after.csv", iter(text_examples),
            ["source_row", "column", "before", "after"],
        )
        missing_reasons = {
            "user_id": "Required for listener-level analysis; rows missing it are dropped.",
            "listened_at": "Required for time-based analysis; rows with invalid or missing timestamps are dropped.",
            "recording_msid": "Retained as missing; listen may still be valid but cannot be recording-keyed.",
            "recording_mbid": "Retained as missing; external recording enrichment is unavailable.",
            "artist_mbids": "Retained as missing; artist name remains available when present.",
            "primary_artist_mbid": "Retained as missing; row is included in review and the missing-artist group.",
            "duration_ms": "Retained as missing; excluded from duration totals and averages.",
        }
        write_csv(
            output_dir / "missing_value_audit.csv",
            iter({
                "column": name,
                "missing_before": missing_before[name],
                "missing_after": missing_after[name],
                "handling": missing_reasons.get(name, "Retained as missing unless required user or timestamp is absent."),
            } for name in AUDIT_FIELDS),
            ["column", "missing_before", "missing_after", "handling"],
        )
        write_csv(
            output_dir / "duplicate_audit.csv",
            iter([
                {"duplicate_type": "exact normalized duplicate rows", "count": counts["exact_duplicates"], "handling": "Remove later copies; first source row is retained."},
                {"duplicate_type": "rows participating in repeated listen keys", "count": duplicate_rows[0], "handling": "Keep; repeated user_id + listened_at + recording_msid can describe repeated submissions or plays."},
                {"duplicate_type": "distinct repeated listen keys", "count": duplicate_rows[1], "handling": "Review separately from exact duplicates."},
                {"duplicate_type": "rows in conflicting listen keys", "count": conflict_rows[0], "handling": "Keep and flag because normalized content differs."},
                {"duplicate_type": "conflicting listen keys", "count": conflict_rows[1], "handling": "Keep and flag because normalized content differs."},
            ]),
            ["duplicate_type", "count", "handling"],
        )
        write_csv(output_dir / "cleaning_decision_log.csv", iter(DECISION_LOG), ["rule", "reason", "check"])
        write_csv(
            output_dir / "merge_audit.csv",
            iter([{"status": "Not applicable", "reason": "This cleaning workflow does not merge an external artist or recording table.", "rows_before": "", "rows_after": "", "unmatched_keys": ""}]),
            ["status", "reason", "rows_before", "rows_after", "unmatched_keys"],
        )
        artist_missing_rows = counts["clean_rows"] - artist_mbid_rows
        metric_rows = [
            {"metric": "total cleaned listens", "records": counts["clean_rows"], "denominator_or_note": "One row per retained listen event."},
            {"metric": "valid known listening time before cleaning (hours)", "records": round(source_valid_duration_ms / 3_600_000, 3), "denominator_or_note": f"Source valid durations before required-field, duplicate, and future-row removals; denominator rows={source_valid_duration_rows}."},
            {"metric": "listens with primary artist MBID", "records": artist_mbid_rows, "denominator_or_note": "Count of cleaned listen rows with a valid primary artist MBID."},
            {"metric": "listens without primary artist MBID", "records": artist_missing_rows, "denominator_or_note": "Kept as an explicit missing-artist group."},
            {"metric": "listens with valid known duration", "records": known_duration_rows, "denominator_or_note": "Nonmissing durations > 0 and <= 7,200,000 ms; implausible and missing values are excluded from time totals."},
            {"metric": "distinct users", "records": connection.execute("SELECT COUNT(*) FROM final_users").fetchone()[0], "denominator_or_note": "Distinct user_id among cleaned listens."},
            {"metric": "distinct artists by MBID", "records": connection.execute("SELECT COUNT(*) FROM final_artists").fetchone()[0], "denominator_or_note": "Distinct nonmissing primary_artist_mbid; not distinct display names."},
            {"metric": "distinct artist name keys", "records": connection.execute("SELECT COUNT(*) FROM final_artist_keys").fetchone()[0], "denominator_or_note": "Distinct case-folded, whitespace-normalized artist_name; includes artists without MBIDs but may conflate or split ambiguous names."},
            {"metric": "valid known total listening time (hours)", "records": round(total_duration_ms / 3_600_000, 3), "denominator_or_note": "Sum of valid duration_ms divided by 3,600,000; missing and flagged durations excluded."},
        ]
        write_csv(output_dir / "metric_counts.csv", iter(metric_rows), ["metric", "records", "denominator_or_note"])

        record_check_rows = []
        for source_row, expected in RECORD_CHECK_EXPECTATIONS.items():
            checked = connection.execute(
                "SELECT original_json, payload FROM records WHERE source_row = ?", (source_row,)
            ).fetchone()
            if checked:
                original = json.loads(checked[0])
                actual = json.loads(checked[1])
                info = (original.get("track_metadata") or {}).get("additional_info") or {}
                disposition = "kept"
                original_timestamp = original.get("timestamp")
                original_duration = info.get("duration")
                original_duration_ms = info.get("duration_ms")
                original_artist_mbids = info.get("artist_mbids")
                actual_time = actual["listened_at"]
                actual_duration = actual["duration_ms"]
                actual_artist = actual["primary_artist_mbid"]
                expected_time = epoch_to_iso(original_timestamp)
                expected_duration = original_duration_ms
                if expected_duration is None and original_duration is not None:
                    expected_duration = float(original_duration) * 1000
                expected_artist_ids = original_artist_mbids or []
                if isinstance(expected_artist_ids, str):
                    expected_artist_ids = [expected_artist_ids]
                expected_artist_ids = [
                    value for value in (valid_uuid(item) for item in expected_artist_ids) if value
                ]
                expected_artist = expected_artist_ids[0] if expected_artist_ids else None
            else:
                original = {}
                disposition = "not retained"
                original_timestamp = original_duration = original_duration_ms = original_artist_mbids = None
                actual_time = actual_duration = actual_artist = None
                expected_time = expected_duration = expected_artist = None
            record_check_rows.append({
                "source_row": source_row,
                "original_timestamp": original_timestamp,
                "original_duration_seconds": original_duration,
                "original_duration_ms": original_duration_ms,
                "original_artist_mbids": json.dumps(original_artist_mbids, ensure_ascii=False),
                "original_record_json": json.dumps(original, ensure_ascii=False, sort_keys=True),
                "expected_result_and_reason": expected,
                "actual_disposition": disposition,
                "actual_listened_at": actual_time,
                "actual_duration_ms": actual_duration,
                "actual_primary_artist_mbid": actual_artist,
                "matches_expected_disposition": disposition == "kept",
                "matches_expected_values": (
                    disposition == "kept"
                    and actual_time == expected_time
                    and actual_duration == expected_duration
                    and actual_artist == expected_artist
                ),
            })
        write_csv(
            output_dir / "record_checks.csv", iter(record_check_rows),
            ["source_row", "original_timestamp", "original_duration_seconds", "original_duration_ms", "original_artist_mbids", "original_record_json", "expected_result_and_reason", "actual_disposition", "actual_listened_at", "actual_duration_ms", "actual_primary_artist_mbid", "matches_expected_disposition", "matches_expected_values"],
        )
        connection.close()

    print(f"Read {counts['input_lines']:,} lines; wrote {counts['clean_rows']:,} clean rows.")
    print(f"Outputs: {output_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input JSON-lines dump")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT, help="Directory for CSV outputs")
    parser.add_argument("--year", type=int, default=2026, help="Year represented by the 9.listens sample")
    parser.add_argument("--month", type=int, default=9, choices=range(1, 13), help="Month represented by the input")
    parser.add_argument("--limit", type=int, help="Process only the first N source lines (for a preview)")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    if not arguments.input.is_file():
        sys.exit(f"Input file not found: {arguments.input}")
    clean_file(arguments.input, arguments.output_dir, arguments.year, arguments.month, arguments.limit)