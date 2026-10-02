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