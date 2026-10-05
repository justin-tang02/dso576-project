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
                "artist_name": record.get("track_metadata", {}).get("artist_name")
            })

            if len(rows) == CHUNK_SIZE:
                chunk = pd.DataFrame(rows)
                parts.append(chunk)
                rows = []

        if len(rows) > 0:
            chunk = pd.DataFrame(rows)
            parts.append(chunk)

artists = pd.concat(parts, ignore_index=True)

print("Shape:")
print(artists.shape)

print("\nDistinct original artist names:")
print(artists["artist_name"].nunique())

artists["artist_key"] = (
    artists["artist_name"]
    .str.strip()
    .str.lower()
)

print("\nDistinct standardized artist names:")
print(artists["artist_key"].nunique())

print("\nDifference:")
print(
    artists["artist_name"].nunique()
    - artists["artist_key"].nunique()
)

examples = (
    artists.groupby("artist_key")["artist_name"]
    .nunique()
)

examples = examples[examples > 1]

print("\nStandardized artist keys with multiple original names:")
print(examples.head(10))

example_keys = examples.head(5).index

for key in example_keys:
    print("\nArtist key:")
    print(key)

    print("Original artist names:")
    print(
        artists.loc[
            artists["artist_key"] == key,
            "artist_name"
        ]
        .drop_duplicates()
        .head(10)
        .to_list()
    )

    artists["artist_key"] = (
    artists["artist_name"]
    .str.strip()
    .str.lower()
)