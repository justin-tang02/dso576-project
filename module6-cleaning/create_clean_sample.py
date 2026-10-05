import zipfile
import json
import pandas as pd

zip_path = "/Users/mjl/Desktop/listenbrainz-listens-dump-2686-20260929-000003-incremental.tar.zip"

rows = []

with zipfile.ZipFile(zip_path) as z:
    listen_file = [
        name for name in z.namelist()
        if name.endswith(".listens")
    ][0]

    with z.open(listen_file) as f:
        for i, line in enumerate(f):
            record = json.loads(line)

            rows.append({
                "user_id": record.get("user_id"),
                "timestamp": record.get("timestamp"),
                "artist_name": record.get("track_metadata", {}).get("artist_name"),
                "track_name": record.get("track_metadata", {}).get("track_name"),
                "recording_msid": record.get("recording_msid")
            })

            if i == 9999:
                break

clean = pd.DataFrame(rows)

clean["listen_time"] = pd.to_datetime(
    clean["timestamp"],
    unit="s",
    utc=True
)

clean["artist_key"] = (
    clean["artist_name"]
    .str.strip()
    .str.lower()
)

clean["track_key"] = (
    clean["track_name"]
    .str.strip()
    .str.lower()
)

print("Cleaned sample shape:")
print(clean.shape)

print("\nCleaned sample columns:")
print(clean.columns)

print("\nFirst 5 cleaned rows:")
print(clean.head())

sample = clean.head(50).copy()

sample.to_csv(
    "module6-cleaning/data_sample/cleaned_sample.csv",
    index=False
)

print("\nSaved:")
print("module6-cleaning/data_sample/cleaned_sample.csv")

print("\nFive record checks:")

check_rows = clean.iloc[[0, 1, 2, 3, 4]].copy()

print(
    check_rows[
        [
            "artist_name",
            "artist_key",
            "track_name",
            "track_key",
            "timestamp",
            "listen_time"
        ]
    ]
)

artist_changed = clean.loc[
    clean["artist_name"] != clean["artist_key"]
].copy()

track_changed = clean.loc[
    clean["track_name"] != clean["track_key"]
].copy()

print("\nArtist changed examples:")
print(
    artist_changed[
        ["artist_name", "artist_key"]
    ].head()
)

print("\nTrack changed examples:")
print(
    track_changed[
        ["track_name", "track_key"]
    ].head()
)

record_checks = clean.iloc[[0, 1, 3, 8, 2]].copy()

record_checks.to_csv(
    "module6-cleaning/outputs/five_record_checks.csv",
    index=False
)

print("\nSaved five record checks:")
print("module6-cleaning/outputs/five_record_checks.csv")