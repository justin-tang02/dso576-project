# Justin Tang - Module 6: Data Cleaning

## Project

Emerging Music Discovery

**Data source:** ListenBrainz incremental listens dump

**Data version:** listenbrainz-dump-2686-20260929-000003-incremental

**Source file:** `9.listens`  

**Git branch:** `justin_part`


## Files

- `cleaning.ipynb` explores the first 10,000 listens, checks the fields and data quality, and documents cleaning decisions.
- `clean_listens.py` processes the full dump, reports validation counts, and writes a small CSV sample for review.
- `cleaned_sample.csv` contains up to 50 cleaned example listens, including a converted UTC datetime.
- '9.listens' contains the full data set. It is kept locally and is not pushed to the repository.

## Cleaning decisions

Leading and trailing whitespace is removed from user, artist, track, and release names. Timestamps are converted to UTC. Rows are kept when the release name is missing or a `recording_msid` is repeated, since either can still describe a listening event. Exact duplicate rows are counted for validation; no rows are removed.

## Run

Keep `9.listens` in this folder. Run all cells in `cleaning.ipynb` to explore and check the sample data. To process the full dump and create `cleaned_sample.csv`, run in the terminal:

```bash
uv run python clean_listens.py
```


## Full-data validation

- **The full data validation is outputed by the clean_listens.py file.**
- Starting rows: 5,022,599
- Final rows: 5,022,599
- Exact duplicates: 0
- Repeated `recording_msid` values: 3,688,434
- Missing `release_name` values: 140,972
- Failed timestamp conversions: 0
- Blank artist names: 0
- Blank track names: 0
- Dates after September 29, 2026: 0

`9.listens` is preserved unchanged and is not committed because of its size.

- Branch: `justin_part`
- Branch URL: https://github.com/justin-tang02/dso576-project/tree/justin_part
- Commit ID: 