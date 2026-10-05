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
                "user_id": record.get("user_id"),
                "timestamp": record.get("timestamp"),
                "recording_msid": record.get("recording_msid")
            })

            # When 100,000 rows have been collected,
            # turn them into a DataFrame
            if len(rows) == CHUNK_SIZE:
                chunk = pd.DataFrame(rows)

                parts.append(chunk)

                # Start a new empty batch
                rows = []

        # Keep the final batch if it has fewer than 100,000 rows
        if len(rows) > 0:
            chunk = pd.DataFrame(rows)
            parts.append(chunk)

# Combine all batches
listens = pd.concat(parts, ignore_index=True)

print("Shape:")
print(listens.shape)

print("\nExact duplicate rows:")
print(listens.duplicated().sum())

print("\nRepeated recording_msid values:")
print(listens["recording_msid"].duplicated().sum())

print("\nDuplicate candidate listen events:")
candidate_duplicates = listens.duplicated(
    subset=["user_id", "timestamp", "recording_msid"]
)

print(candidate_duplicates.sum())

print("\nExample duplicate candidate rows:")
print(
    listens.loc[candidate_duplicates].head()
)