# Module 6 Data Cleaning

## Cleaning Decision Log

| Rule | Reason | Check |
|---|---|---|
| Convert Unix `timestamp` to UTC `listen_time` | Makes listening time easier to interpret for date-based analysis | Full-data minimum and maximum timestamps converted successfully |
| Keep original `artist_name` and create lowercase `artist_key` | Case differences can split the same artist into separate groups | 280,001 original artist names vs. 270,880 standardized names |
| Keep original `track_name` and create lowercase `track_key` | Case differences can split track labels into separate groups | 722,720 original track names vs. 674,920 standardized names |
| Keep repeated `recording_msid` values | The same recording can appear in many valid listening events | 3,688,434 repeated `recording_msid` values but 0 duplicate candidate listen events |
| Do not drop rows for missing core fields | No missing values were found in the checked core columns | 0 missing in `user_id`, `timestamp`, `artist_name`, `track_name`, and `recording_msid` |
| Keep unusual old timestamps | Older listens may be historical listening records rather than invalid dates | Full listening-time range is 2005-02-13 to 2026-09-28 |

## Data Source

Source: ListenBrainz incremental listens dump

Archive:
`listenbrainz-listens-dump-2686-20260929-000003-incremental.tar.zip`

Full dataset row count: 5,022,599 listening records

One row represents one submitted listening event for one user at one timestamp.

The original archive is kept unchanged outside the repository. Only cleaned samples and analysis outputs are stored in this branch.

## Run Instructions
Activate the DSO 576 course environment, then run the scripts from the repository root.

Example:

```bash
source /Users/mjl/dso576/.venv/bin/activate
python module6-cleaning/full_inspections.py
python module6-cleaning/duplicate_inspection.py
python module6-cleaning/artist_name_inspection.py
python module6-cleaning/track_name_inspection.py
python module6-cleaning/create_clean_sample.py
```

## Expected Output Files

- `data_sample/cleaned_sample.csv`
- `outputs/five_record_checks.csv`

