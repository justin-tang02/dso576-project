# Homework 6: ListenBrainz data cleaning

**Student:** Sizhou Wang (confirm spelling before submission)
**Project:** Emerging Music Artist
**Source:** local `9.listens` from the team's ListenBrainz data work. The download date is not documented here. The exact file used has SHA-256 `54cfe730df6eaf3aac9dd16421a262f96fd69887a6216658c699ec738bb75fcb` and size 3,214,994,924 bytes. The original file is read but never modified.

## Run

From this directory, install the environment with `UV_CACHE_DIR=/private/tmp/uv-cache-homework6 uv sync --frozen`. Open `Homework6.ipynb` with the `dso576-project` Python 3.13 kernel and choose **Restart Kernel and Run All**. The notebook includes the full code, executed results, the 14-item checklist, cleaning decision log, and five original/expected/actual record checks. `homework6_clean.py` is an exported script of the same notebook code and can be run with `.venv/bin/python homework6_clean.py` from this directory.

## Expected outputs

| File | Purpose |
|---|---|
| `Homework6.ipynb` | Code and saved results; main individual work |
| `homework6_clean.py` | Script export for command-line reruns |
| `outputs/homework6_clean.parquet` | Full cleaned event table (generated locally; not committed) |
| `outputs/homework6_sample.csv` | 20 review rows, including five difficult cases |

The full cleaned table keeps all 5,022,599 source events. It standardizes outer whitespace, converts Unix seconds to UTC, derives durations in milliseconds when present, and flags old or implausible events. It does not infer missing MusicBrainz IDs or remove possible repeat listens.

## Submission details

The PDF assignment also requires an individual Gradescope PDF and a push to an individual GitHub branch. The current local branch is `siz_datafit`. **Branch URL and submitted commit ID: pending commit/push.** Add those exact details to this README and the PDF after submission preparation. Do not commit the 3 GB raw source or the generated full Parquet.
