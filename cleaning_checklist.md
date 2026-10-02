# Project Data Cleaning Assignment

**Project:** Emerging Artist Exposure and Listener Engagement  
**Student:** Soonwon Hwang  
**Course:** DSO 576  
**Data file:** ListenBrainz September 2026 listens, local file `9.listens`  
**Report date:** October 1, 2026

## Project Question

**Vision:** A music editorial lead at a music-streaming platform must decide which emerging artists should receive additional playlist and promotional exposure.

**Business question:** Which artists in the observed ListenBrainz period have listener reach and repeat listening that merit further editorial review for exposure?

**Main measures:** Listen count and distinct listeners per normalized artist name, with artist MBID as the preferred entity key where available. Listen counts by period can measure growth when multiple periods are available. Missing artist names remain a separate group; missing MBIDs do not remove a named artist from name-based counts. These observational counts describe association and activity; they do not show that promotion caused listening growth.

## Data and Reproducibility

**Source:** ListenBrainz public data dumps, listens data, https://listenbrainz.org/data/  
**Partition/version label:** `9.listens` suggests September; the first records have September 2026 timestamps. The full file is not confined to that month, with 3,607,337 of 5,022,599 rows flagged outside September 2026. No release manifest is supplied, so exact publication time and intended coverage are unresolved.  
**Source preservation:** `9.listens` is read-only from the cleaner's perspective. The script streams the JSONL file and writes derived files under `outputs/`. The repository sample `data_sample.jsonl` contains the first 100 original records.  
**Full run:** `python clean_listens.py`  
**Preview:** `python clean_listens.py --limit 10000 --output-dir outputs/preview`  
**Notebook:** Open `clean_listens.ipynb` and run all cells in order; it processes a bounded preview.  
**Dependencies:** Python 3.9+; notebook packages listed in `requirements.txt`. The cleaner itself uses only the Python standard library.

The supported executable is `clean_listens.py`. The pre-existing `plan.py` is an earlier analysis draft and is not used by the README run command or notebook because its assumptions do not match the observed `9.listens` schema.

## Cleaning Decision Log

| Rule | Reason | Check |
|---|---|---|
| Parse source `timestamp` as Unix seconds and write UTC ISO-8601. | The ListenBrainz rows use a top-level epoch timestamp; a normalized time is needed for time comparisons. | `type_conversion_log.csv` and `record_checks.csv`. |
| Trim text and collapse repeated whitespace while preserving display-name case. | Remove formatting noise without changing artist or track capitalization. | `text_standardization_log.csv` and `text_before_after.csv`. |
| Convert legacy `duration` seconds to milliseconds; preserve `duration_ms`. | The sample contains both duration representations. | `type_conversion_log.csv` and source rows 1-5 in `record_checks.csv`. |
| Keep valid UUID-shaped MBIDs, lowercase them, and retain all credited artist IDs. | IDs support later artist-level grouping; malformed IDs cannot join reliably. | `listens_clean.csv`, `missing_value_audit.csv`, and `record_checks.csv`. |
| Remove later exact normalized duplicates; retain and flag different content sharing a candidate listen key. | Exact duplicate submissions add no event information; a repeated key with different payload may represent a distinct event or conflicting submission. | `duplicate_audit.csv` and `data_quality_flags.csv`. |
| Drop rows without `user_id` or a parseable timestamp; retain other missing metadata. | Required identity/time fields are needed for listener/time analysis, while incomplete metadata can still represent a real listen. | `missing_value_audit.csv` and `cleaning_summary.csv`. |
| Remove future-dated listens; flag out-of-month and implausible-duration rows. | Future listens are impossible at run time; other unusual values need review rather than automatic deletion. | `data_quality_flags.csv` and `cleaning_summary.csv`. |
| Flag users above the 99.5th percentile of retained listen counts. | Heavy use is unusual, but not necessarily erroneous. | `data_quality_flags.csv`. |

## Fourteen-Item Checklist

Full-run evidence is copied into `submission_evidence/`; full-size data CSVs remain in the ignored local `outputs/` directory. The unbounded run processed the full local source file. Afterward, the final additive audit fields were verified with the included 100-record source sample; a second complete-dump run for those last reporting-only additions was cancelled before completion. The full cleaned CSV and reconciliation below are from the completed earlier full run. The five field-level record checks are current and were generated on source lines 1-5 from the 100-record sample.

### 1. State the project vision and question

**Status:** Done  
**Evidence:** Vision and business question are stated above and in `README.md`. Main comparisons are listen count and distinct listeners by artist. Promotion effects are not identifiable from listening histories alone.

### 2. Define one row

**Status:** Done  
**Evidence:** One source row is one user's listen event. Candidate event key: `user_id + listened_at + recording_msid`. It is not assumed to be globally unique: `duplicate_audit.csv` reports repeated keys and the cleaner retains/flags conflicting content.

### 3. Preserve the source

**Status:** Unresolved: exact dump release metadata is not supplied.  
**Evidence:** ListenBrainz public data dumps, listens; local `9.listens`; the filename suggests a September partition and the first records are dated September 2026, but the full file has broad out-of-month coverage. The cleaner does not edit the original. The exact publication date, source manifest, and intended time coverage are unavailable. The 3.0 GB source is not committed because GitHub rejects regular files over 100 MB; the branch includes the first 100 original JSONL records as `data_sample.jsonl`. The instructor can obtain the source from the public ListenBrainz data-dumps page. See `README.md`.

### 4. Inspect columns and types

**Status:** Done  
**Evidence:** `submission_evidence/type_conversion_log.csv` reports 5,022,599 timestamps converted with 0 failures, 2,711,476 known duration values with 0 conversion failures, and 0 invalid UUID-shaped MBID values. The source contains legacy `duration` seconds and `duration_ms`; the cleaner converts seconds to milliseconds and preserves milliseconds. The original 3.0 GB file remains unchanged.

### 5. Standardize text

**Status:** Done  
**Evidence:** `submission_evidence/text_standardization_log.csv` reports 517 user-name, 510 artist-name, 3,756 track-name, and 2,517 release-name changes; 58 blank release names became missing. `submission_evidence/text_before_after.csv` includes concrete examples. For example, source row 331 changed `I Don't Know What to Do  (Extended Mix)` to `I Don't Know What to Do (Extended Mix)`. Display-name case is preserved.

### 6. Investigate duplicates

**Status:** Done  
**Evidence:** `submission_evidence/duplicate_audit.csv` reports 0 exact normalized duplicate rows, 0 rows in repeated listen keys, and 0 conflicting keys. Thus no rows were removed for duplication. Exact duplicates would be removed; different records sharing the candidate key would be retained and flagged.

### 7. Handle missing data

**Status:** Done  
**Evidence:** `submission_evidence/missing_value_audit.csv` has before/after counts by field. Of 5,022,599 rows, 4,801,159 have no primary artist MBID, 4,844,752 have no recording MBID, 141,030 have no release name, and 2,311,123 have no duration. No rows lack `user_id` or a parseable timestamp. Missing metadata stays missing; unknown duration is excluded from duration totals.

### 8. Check suspicious values

**Status:** Done, with a material period limitation noted below.  
**Evidence:** `submission_evidence/data_quality_flags.csv` reports 3,607,337 out-of-month rows, 0 future timestamps, 316 implausible durations, 0 key conflicts, and 3,786,192 heavy-user rows. Future dates would be removed; this run found none. Other flagged rows are retained. The high out-of-month count means `9.listens` is not cleanly restricted to September 2026; month-specific conclusions require filtering to the intended period or confirming the dump partition.

### 9. Verify merges

**Status:** Not applicable  
**Evidence:** No external artist or recording table is merged in this cleaning workflow. `merge_audit.csv` records this explicitly; there are no merge keys, unmatched merge keys, or merge-induced row changes.

### 10. Reconcile changes

**Status:** Done  
**Evidence:** `submission_evidence/cleaning_summary.csv` reports 5,022,599 input lines, 0 missing required user/time rows, 0 exact duplicates, 0 future listens, and 5,022,599 final rows. Reconciliation: 5,022,599 - 0 - 0 - 0 = 5,022,599. `submission_evidence/metric_counts.csv` reports 161,891.784 hours of valid known duration after cleaning; because no rows were removed, the valid source total is also 161,891.784 hours. There are 2,711,160 valid-duration rows.

### 11. Check calculations

**Status:** Done, with low artist-ID coverage limiting entity-level analysis.  
**Evidence:** `submission_evidence/metric_counts.csv` reports 5,022,599 listens, 24,625 distinct users, 2,711,160 valid known durations, and 25,124 distinct MBIDs. Only 221,440 listens have a primary artist MBID; the remaining 4,801,159 are retained in the missing-MBID group. Duration sums exclude missing or implausible durations. User denominators use nonmissing `user_id`. The low MBID coverage and display-name ambiguity should be addressed before making artist-level conclusions.

### 12. Verify individual records

**Status:** Done  
**Evidence:** `submission_evidence/record_checks.csv` contains source lines 1-5, original JSON and values, expected result/reason, actual values, and separate disposition/value match checks. All five `matches_expected_disposition` and all five `matches_expected_values` values are true. Cases include seconds-to-milliseconds conversion (line 1), preservation of existing millisecond durations (lines 2-5), and missing artist MBIDs retained as missing.

| Source row | Original source values | Expected result | Actual result | Match |
|---|---|---|---|---|
| 1 | `timestamp=1790545436`; `duration=112` seconds; artist MBID absent. | Keep; convert timestamp to UTC and duration to 112000 ms; retain missing artist MBID. | Kept; `2026-09-27T21:43:56Z`; `112000` ms; artist MBID missing. | Yes |
| 2 | `timestamp=1790553602`; `duration_ms=186860`; artist MBID `0976dbd8-e7fe-4161-9a49-58c57f7a7787`. | Keep; convert timestamp; preserve milliseconds and valid artist MBID. | Kept; `2026-09-28T00:00:02Z`; `186860` ms; MBID preserved. | Yes |
| 3 | `timestamp=1790553558`; `duration_ms=87085`; artist MBID absent. | Keep; convert timestamp; preserve milliseconds and missing MBID. | Kept; `2026-09-27T23:59:18Z`; `87085` ms; artist MBID missing. | Yes |
| 4 | `timestamp=1790553524`; `duration_ms=157361`; artist MBID absent. | Keep; convert timestamp; preserve milliseconds and missing MBID. | Kept; `2026-09-27T23:58:44Z`; `157361` ms; artist MBID missing. | Yes |
| 5 | `timestamp=1790553534`; `duration_ms=128000`; artist MBID absent. | Keep; convert timestamp; preserve milliseconds and missing MBID. | Kept; `2026-09-27T23:58:54Z`; `128000` ms; artist MBID missing. | Yes |

### 13. Test reproducibility

**Status:** Partially done: a full cleaner run completed, but an exact full rerun of the final additive audit schema is still needed.  
**Evidence:** The completed full run read all 5,022,599 source lines and wrote 5,022,599 clean rows. Its reconciliation, quality, missingness, and metric reports are in `submission_evidence/`. After later report-only additions, the full rerun was cancelled; the final script was instead rerun against all 100 records in `data_sample.jsonl`, and its five field-level checks all passed. To claim exact full-version reproducibility, run `python clean_listens.py` from the project directory after the final changes. The notebook remains a bounded 10,000-line demonstration.

### 14. Document remaining limitations

**Status:** Done  
**Evidence:** The exact dump release date is unknown; ListenBrainz contributors may not represent all streaming listeners; an observed first listen may not be a true discovery; 95.6% of listens have no primary artist MBID; 71.8% are flagged outside the September 2026 period; durations are absent for 46.0% of records; this workflow does not merge MusicBrainz metadata; observational listening associations cannot establish the causal effect of editorial exposure. These limitations affect time-window validity, generalization, artist matching, and causal interpretation.

## Checking a Codex Suggestion

**Suggestion checked:** Convert legacy `track_metadata.additional_info.duration` values from seconds to milliseconds while leaving `duration_ms` values unchanged. I checked original JSON source lines 1-5 before accepting the rule: line 1 has `duration: 112`, while lines 2-5 have `duration_ms` values. `record_checks.csv` confirms line 1 becomes 112000 ms and the existing values (186860, 87085, 157361, and 128000) are preserved. Review the source records and actuals rather than treating the generated explanation as proof by itself.

## Sample Selection

`submission_evidence/sample_50_rows.csv` contains up to 50 full-run cleaned rows. Selection prioritizes up to 25 earliest-source-row difficult records with a quality flag or missing primary artist MBID, then fills remaining positions with ordinary rows selected by a stable SHA-256 ranking of source-row number. This deterministic rule shows cases requiring review while remaining reproducible. The tracked `cleaned_sample_50_rows.csv` is generated from the first 100 original records in `data_sample.jsonl` for a compact runnable example.

## Individual GitHub Submission

**Branch name:** `leo_part`  
**Branch URL:** https://github.com/justin-tang02/dso576-project/tree/leo_part  
**Submitted commit ID:** [will be filled after the deliverables commit]  
**Instructor repository access:** Not verified; confirm the instructor has access in GitHub repository settings before submission.

Do not submit this assignment to `main` or the shared course repository. The commit ID must identify the commit containing the submitted deliverables.