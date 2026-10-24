# Jay Lai — Emerging Artists Discoveryt Data Cleaning

## Data source
ListenBrainz incremental listens dump:
`listenbrainz-listens-dump-2686-20260929-000003-incremental`

The original file is `listens/2026/9.listens`. It is kept in my Downloads folder and is not included in this repository.

## How to run
1. Extract the ListenBrainz dump into Downloads.
2. Install the dependency: `pip install -r requirements.txt`
3. Open `cleaning_jay.ipynb` in VS Code.
4. Restart the kernel and run all cells from the top.

## Outputs
- `cleaned_50_jay.csv`: 50 cleaned rows, including rows with missing optional fields and rows with a date value.
- `cleaning_jay.py`: Python export of the notebook.

The notebook currently loads 10,000 listens from the file. Results calculated in the notebook apply to those 10,000 rows.

## GitHub submission
Branch: `jay-lai`  
Branch URL: https://github.com/justin-tang02/dso576-project/tree/jay-lai  
Commit ID: f990dbb5eaefdf91ce0ff03e2d120a45dd25acf8

---

# ListenBrainz Listen Cleaning

This project prepares ListenBrainz listening events for an emerging-artist exposure analysis. A music editorial lead asks which artists have listener reach and repeat engagement that may justify additional exposure. Main comparisons are listens and distinct listeners by artist; these observational data do not establish that promotion caused listening growth.

The full local JSON-lines dump is `9.listens` (about 3.0 GB; one listen per line). The repository-sized `data_sample.jsonl` contains the first 100 original records for inspection and a quick run. The cleaner reads incrementally and never modifies either source file.

## Data Source

- **Source:** ListenBrainz public data dumps, listens data: https://listenbrainz.org/data/
- **Local file:** `9.listens` in the project root
- **Version represented here:** September 2026 listens, inferred from the filename and observed timestamps. The supplied dump has no release manifest, so its precise publication timestamp is unknown.
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

Open `clean_listens.ipynb` in Jupyter or VS Code and run its cells in order for schema inspection and a 10,000-line preview. The notebook writes to `outputs/notebook_preview/` and does not overwrite the full-run outputs.

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

The SQLite index used for global de-duplication is temporary and is removed when the run finishes. The original `9.listens` file is never modified.

## Individual Submission

- **Current branch:** `leo_part`
- **Branch URL:** https://github.com/justin-tang02/dso576-project/tree/leo_part
- **Submitted commit ID:** 098df0f
- **Instructor repository access:** confirm access before submission.
