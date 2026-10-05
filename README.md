# ListenBrainz Listen Cleaning

This project prepares ListenBrainz listening events for an emerging-artist exposure analysis. A music editorial lead asks which artists have listener reach and repeat engagement that may justify additional exposure. Main comparisons are listens and distinct listeners by artist; these observational data do not establish that promotion caused listening growth.

The full local JSON-lines dump is `9.listens` (about 3.0 GB; one listen per line). The repository-sized `data_sample.jsonl` contains the first 100 original records for inspection and a quick run. The cleaner reads incrementally and never modifies either source file.

## Data Source

- **Source:** ListenBrainz public data dumps, listens data: https://listenbrainz.org/data/
- **Local file:** `9.listens` in the project root
- **Partition/version label:** The filename `9.listens` suggests a September partition; the first records have September 2026 timestamps. The full file is not confined to September 2026: the completed run flagged 3,607,337 of 5,022,599 records as outside that month. No release manifest is supplied, so exact publication time and intended time coverage remain unknown.
- **Repository sample:** `data_sample.jsonl`, first 100 source records, unchanged JSONL records from `9.listens`.
- **Cleaned sample:** `cleaned_sample_50_rows.csv`, up to 50 rows from cleaning that compact input; it prioritizes difficult records and fills remaining space with reproducibly selected ordinary rows.
- **Observed format and grain:** newline-delimited JSON; one user listen per row. Top-level event time is `timestamp`; track and artist metadata are nested in `track_metadata`, with IDs and duration in `track_metadata.additional_info`.

## Setup and Run

Python 3.9 or newer is required. The cleaner itself uses only the standard library. Install the notebook dependencies with:

```sh
python -m pip install -r requirements.txt
```

`clean_listens.py` is the supported cleaner. The pre-existing `plan.py` is an earlier analysis draft and is not used by the notebook or the run commands below because its field assumptions do not match the observed source schema.

Run the full file from the project directory:

```sh
python clean_listens.py
```

The defaults treat this input as September 2026 and write to `outputs/`. Override the input, reporting month, or output directory as needed:

```sh
python clean_listens.py --input 9.listens --year 2026 --month 9 --output-dir outputs
```

For a quick bounded run, process the first 10,000 source lines:

```sh
python clean_listens.py --limit 10000 --output-dir outputs/preview
```

Open `clean-data.ipynb` in Jupyter or VS Code and run its cells in order for schema inspection and a 10,000-line preview. The notebook writes to `outputs/notebook_preview/` and does not overwrite the full-run outputs.

To run the small repository sample instead:

```sh
python clean_listens.py --input data_sample.jsonl --limit 100 --output-dir outputs/sample
```

## Cleaning Rules

- Normalize ListenBrainz `timestamp` to UTC ISO-8601 and nested text fields by trimming and collapsing whitespace.
- Convert `duration` seconds to milliseconds when `duration_ms` is absent; preserve an existing `duration_ms` value.
- Keep valid UUID-shaped recording and artist MBIDs; preserve all valid artist MBIDs as a pipe-separated list and retain the first as the primary artist.
- Drop rows without a usable user ID or timestamp, remove exact duplicate normalized rows, and remove future-dated listens.
- Keep unusual-but-possible records, flagging conflicting listen keys, events outside the selected month, invalid duration ranges, unusually heavy users, and missing primary artist MBIDs for review.

## Expected Output Files

The selected output directory contains cleaned data and audit evidence for the assignment:

- `listens_clean.csv`: cleaned listen rows with source line number and quality flags.
- `needs_review.csv`: cleaned rows with one or more quality flags or no primary artist MBID.
- `sample_50_rows.csv`: up to 50 deterministic cleaned rows, prioritizing difficult cases and then ordinary cases.
- `cleaning_summary.csv`: input, removal, and output row counts.
- `data_quality_flags.csv`: counts of suspicious-value flags, including removed future listens.
- `cleaning_decision_log.csv`: each rule, rationale, and its evidence check.
- `type_conversion_log.csv`: known values, failed conversions, and duration source units.
- `text_standardization_log.csv` and `text_before_after.csv`: standardization counts and up to 10 original/result examples.
- `duplicate_audit.csv`: exact duplicates, repeated listen keys, and key conflicts.
- `missing_value_audit.csv`: per-column missing counts before/after cleaning and handling decisions.
- `merge_audit.csv`: records that no external-table merge was performed.
- `metric_counts.csv`: metric counts and denominator notes, including missing-artist and unknown-duration handling.
- `record_checks.csv`: five predeclared expectations with original source records and actual cleaned results.

Compact copies of the full-run audit reports and 50-row sample are tracked under `submission_evidence/`; the large full cleaned CSVs stay local in the ignored `outputs/` folder.

The recorded full-run totals are from the successful unbounded run. The final additions to the audit schema were checked against the included 100-row source sample; a second full-dump run after those final reporting additions was cancelled. Rerun `python clean_listens.py` to regenerate the complete output set with the exact current script before claiming full-version reproducibility.

The SQLite index used for global de-duplication is temporary and is removed when the run finishes. The original `9.listens` file is never modified.