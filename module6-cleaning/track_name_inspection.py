import zipfile
import json
import pandas as pd

zip_path = "/Users/mjl/Desktop/listenbrainz-listens-dump-2686-20260929-000003-incremental.tar.zip"

CHUNK_SIZE = 100_000

rows = []
parts = []

with zipfile.ZipFile(zip_path) as z:
    listen_file = [
        name for name in z.namelist()
        if name.endswith(".listens")
    ][0]

    with z.open(listen_file) as f:
        for line in f:
            record = json.loads(line)

            rows.append({
                "track_name": record.get("track_metadata", {}).get("track_name")
            })

            if len(rows) == CHUNK_SIZE:
                chunk = pd.DataFrame(rows)
                parts.append(chunk)
                rows = []

        if len(rows) > 0:
            chunk = pd.DataFrame(rows)
            parts.append(chunk)

tracks = pd.concat(parts, ignore_index=True)

print("Shape:")
print(tracks.shape)

print("\nDistinct original track names:")
print(tracks["track_name"].nunique())

tracks["track_key"] = (
    tracks["track_name"]
    .str.strip()
    .str.lower()
)

print("\nDistinct standardized track names:")
print(tracks["track_key"].nunique())

print("\nDifference:")
print(
    tracks["track_name"].nunique()
    - tracks["track_key"].nunique()
)

examples = (
    tracks.groupby("track_key")["track_name"]
    .nunique()
)

examples = examples[examples > 1]

print("\nStandardized track keys with multiple original names:")
print(examples.head(10))

example_keys = examples.head(5).index

for key in example_keys:
    print("\nTrack key:")
    print(key)

    print("Original track names:")
    print(
        tracks.loc[
            tracks["track_key"] == key,
            "track_name"
        ]
        .drop_duplicates()
        .head(10)
        .to_list()
    )