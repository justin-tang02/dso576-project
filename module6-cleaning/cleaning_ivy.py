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

            if i == 999:
                break

df = pd.DataFrame(rows)

print(df.head())
print(df.shape)
print(df.columns)
print(df.dtypes)

print("\nMissing values:")
print(df.isna().sum())

print("\nExact duplicate rows:")
print(df.duplicated().sum())

print("\nRepeated recording_msid values:")
print(df["recording_msid"].duplicated().sum())

print("\nDuplicate candidate listen events:")
print(
    df.duplicated(
        subset=["user_id", "timestamp", "recording_msid"]
    ).sum()
)

df["listen_time"] = pd.to_datetime(
    df["timestamp"],
    unit="s",
    utc=True
)

print("\nTimestamp range:")
print(df["listen_time"].min())
print(df["listen_time"].max())

print("\nArtist names with leading/trailing spaces:")
artist_spaces = (
    df["artist_name"]
    != df["artist_name"].str.strip()
)
print(artist_spaces.sum())

print("\nTrack names with leading/trailing spaces:")
track_spaces = (
    df["track_name"]
    != df["track_name"].str.strip()
)
print(track_spaces.sum())


print("\nEmpty artist names:")
print((df["artist_name"] == "").sum())

print("\nEmpty track names:")
print((df["track_name"] == "").sum())