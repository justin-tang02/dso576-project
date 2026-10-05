import zipfile
import json
import pandas as pd

zip_path = "/Users/mjl/Desktop/listenbrainz-listens-dump-2686-20260929-000003-incremental.tar.zip"

row_count = 0

missing_user_id = 0
missing_timestamp = 0
missing_artist_name = 0
missing_track_name = 0
missing_recording_msid = 0

min_timestamp = None
max_timestamp = None

with zipfile.ZipFile(zip_path) as z:
    listen_file = [
        name for name in z.namelist()
        if name.endswith(".listens")
    ][0]

    with z.open(listen_file) as f:
        for line in f:
            record = json.loads(line)

            row_count += 1

            user_id = record.get("user_id")
            timestamp = record.get("timestamp")
            artist_name = record.get("track_metadata", {}).get("artist_name")
            track_name = record.get("track_metadata", {}).get("track_name")
            recording_msid = record.get("recording_msid")

            if user_id is None:
                missing_user_id += 1

            if timestamp is None:
                missing_timestamp += 1

            if artist_name is None:
                missing_artist_name += 1

            if track_name is None:
                missing_track_name += 1

            if recording_msid is None:
                missing_recording_msid += 1

            if timestamp is not None:
                if min_timestamp is None or timestamp < min_timestamp:
                    min_timestamp = timestamp

                if max_timestamp is None or timestamp > max_timestamp:
                    max_timestamp = timestamp

print("Total rows:")
print(row_count)

print("\nMissing user_id:")
print(missing_user_id)

print("\nMissing timestamp:")
print(missing_timestamp)

print("\nMissing artist_name:")
print(missing_artist_name)

print("\nMissing track_name:")
print(missing_track_name)

print("\nMissing recording_msid:")
print(missing_recording_msid)

print("\nMinimum timestamp:")
print(min_timestamp)

print("\nMaximum timestamp:")
print(max_timestamp)

min_listen_time = pd.to_datetime(
    min_timestamp,
    unit="s",
    utc=True
)

max_listen_time = pd.to_datetime(
    max_timestamp,
    unit="s",
    utc=True
)

print("\nMinimum listen time:")
print(min_listen_time)

print("\nMaximum listen time:")
print(max_listen_time)

