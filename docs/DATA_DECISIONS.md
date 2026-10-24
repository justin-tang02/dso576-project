# Team Data Reconciliation (Phase 2)

This file records how the six Module 6 cleaning branches were compared and which rule became canonical on `main`. BUILD_SPEC.md and the `analysis/` code use these definitions and no others.

## Branches compared

| Member | Branch | Tool | Scope of checks |
|---|---|---|---|
| Leo | `leo_part` | `clean_listens.py` (stdlib, streaming) | Full file, 5,022,599 rows, full audit CSVs |
| Justin | `justin_part` | `clean_listens.py` + notebook | Full file counts; 10,000-row notebook |
| Jay | `jay-lai` | pandas notebook | First 10,000 rows |
| Ivy | `cleaning-ivy` | pandas scripts | Full file for keys, duplicates, missingness |
| Toby | `cleaning-toby` | pandas notebook (README shared with Leo's cleaner) | First 10,000 rows |
| Sizhou | `siz_datafit` | DuckDB notebook | Full file, Parquet output, SHA-256 |

Where the full-file numbers overlap, they agree: 5,022,599 rows, 24,625 users, 0 exact duplicates, 0 repeated `user_id + timestamp + recording_msid` keys, 0 missing user, time, artist or track, 4,801,159 rows without artist MBIDs, 4,844,752 without recording MBIDs, 2,311,123 without duration.

## Source, as agreed

`listens/2026/9.listens` from **ListenBrainz incremental dump 2686** (`listenbrainz-listens-dump-2686-20260929-000003-incremental`, identified by Justin, Jay and Ivy). Size 3,214,994,924 bytes, SHA-256 `54cfe730df6eaf3aac9dd16421a262f96fd69887a6216658c699ec738bb75fcb` (Sizhou). Listen times run from 2005-02-13 23:55:46 to 2026-09-28 23:56:23 UTC (Sizhou, Ivy).

Consequence: this is one incremental dump, not complete user histories. 71.8% of rows fall outside September 2026 (Leo), mostly historical listens submitted in bulk. That replaces the Phase 1 assumption of "complete listening histories" and is why the dashboard shows a data sufficiency check (BUILD_SPEC.md, Data Notes).

## Disagreements and resolutions

| # | Issue | What members did | Canonical decision | Where |
|---|---|---|---|---|
| 1 | Unit of analysis | All: one submitted listen. Candidate key `user_id + timestamp + recording_msid`, 0 repeats (Leo, Sizhou, Ivy, Jay full or sample). Justin counted repeated `recording_msid` (3,688,434), which are normal replays. | One row per listen. Repeated `recording_msid` is not a duplicate. | `clean_listens.py` |
| 2 | Duplicates | Leo removes exact normalized duplicates and flags key conflicts; others count only. All found 0. | Keep Leo's rule (remove exact, flag conflicts). No rows are affected in this dump. | `clean_listens.py` |
| 3 | Display text | Justin, Jay, Ivy, Sizhou trim ends only. Leo and Toby also collapse inner whitespace (510 artist and 3,756 track names have double spaces, e.g. source row 331). | Trim and collapse whitespace, keep case. Double spaces would otherwise split one artist into two keys. | `analysis/keys.py: clean_text` |
| 4 | Artist grouping key | Toby: artist MBID only, excluding rows without one. Ivy: `strip().lower()` (280,001 names to 270,880 keys). Leo: whitespace + casefold. Sizhou: raw name, warns about namesakes. | `artist_key = NFKC(clean_text(artist_name)).casefold()`. MBID-only grouping is rejected because it drops 95.6% of listens, and those are disproportionately small artists. NFKC folds full-width variants (`ＢＴＳ` to `bts`). | `analysis/keys.py: normalize_key` |
| 5 | Track key | Only Ivy built one (722,720 names to 674,920 keys). | Adopt Ivy's idea with the same normalizer: `track_key = normalize_key(track_name)`. Used for entry tracks and distinct tracks. | `clean_listens.py` |
| 6 | MBIDs | All keep missing as missing; Sizhou explicitly rejects name-to-MBID inference. Toby and Jay's flattened columns show a rare `track_metadata.mbid_mapping`. | Keep missing. Read `additional_info` first, `mbid_mapping` as fallback. MBID is a display attribute (link to MusicBrainz), never the grouping key. No MusicBrainz merge in the MVP. | `clean_listens.py` |
| 7 | Collaborations | Leo keeps all IDs and the first as primary; Sizhou keeps the array (16,648 multi-MBID rows). | The credit string is the entity (`"G Jones, Eprom"` is one artist_key). Splitting credits is post-MVP. | `analysis/keys.py` |
| 8 | Missing release name | Justin 140,972; Leo and Sizhou 141,030. The 58 difference is blank strings. | Blank text is missing (141,030). Release is not used by any metric. | `clean_text` |
| 9 | Future cutoff | Leo: run time. Justin, Jay: after 2026-09-29. Toby: after 2026-10-05. All found 0. | Fixed cutoff at the dump creation time, 2026-09-29T00:00:03Z (`--as-of`), so reruns are identical. | `clean_listens.py` |
| 10 | Old listens | Sizhou flags pre-2010 (48,265); Ivy keeps all; Leo flags outside September. | Keep all rows. Outside-window rows are used only to decide whether a listener is new to an artist. | `analysis/pairs.py` |
| 11 | Analysis period | Leo and Toby: September 2026. Ivy: 28-day growth. Jay: last 28 days. | Window = 2026-09-01 to 2026-09-28 UTC (28 days ending on the last observed day). | `analysis/config.py` |
| 12 | Duration | Leo flags `<= 0` or `> 2 h` (316); Sizhou and Toby flag `> 24 h` (1). | Keep Leo's 2 h flag. Duration feeds no dashboard metric, so the choice does not change results. | `clean_listens.py` |
| 13 | Heavy users | Only Leo flags users above the 99.5th percentile of listens (3,786,192 rows). | Keep the flag; the dashboard offers an "Exclude heavy users" population built from it. | `analysis/load.py` |
| 14 | Non-artist credits | Not addressed by anyone. | Exclude `various artists`, `unknown`, `[unknown]` and similar (list in `NON_ARTIST_KEYS`) from artist metrics only. | `analysis/keys.py` |

## Rerun needed on the full file

Rules 3 to 6 and 9 changed the cleaner, so `submission_evidence/` holds the Module 6 run and will differ slightly in distinct artist keys. Regenerate with the commands in README.md ("Full pipeline"); the row counts above should not change.
