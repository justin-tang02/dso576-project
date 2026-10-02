# %%
import json
from itertools import islice
from pathlib import Path
import pandas as pd

file = (
    Path.home()
    / "Downloads"
    / "listenbrainz-listens-dump-2686-20260929-000003-incremental"
    / "listens"
    / "2026"
    / "9.listens"
)

print("File found:", file.exists())

if file.exists():
    print("File size (MB):", round(file.stat().st_size / 1_000_000, 2))
    with file.open(encoding="utf-8") as f:
        records = [json.loads(line) for line in islice(f, 10000)]

    data = pd.json_normalize(records)
    print(f"Loaded {len(data)} listens")
    display(data.head())

# %%
data

# %%
clean = data.copy()

# %%
clean.iloc[[0]]

# %%
data.dtypes

# %%
clean = data.copy()

clean["listen_datetime"] = pd.to_datetime(
    data["timestamp"], unit="s", utc=True, errors="coerce"
)

failed = data["timestamp"].notna() & clean["listen_datetime"].isna()

clean[["timestamp", "listen_datetime"]].head(5)

# %%
print("Rows checked:", len(data))
print("Failed conversions:", failed.sum())

# %%
print(data["track_metadata.artist_name"].head())

# %%
clean["track_metadata.artist_name"] = data["track_metadata.artist_name"].str.strip()

# %%
print(clean["track_metadata.artist_name"].head())

# %%
artistclean = data["track_metadata.artist_name"].notna() & (
    data["track_metadata.artist_name"] != clean["track_metadata.artist_name"]
)

# %%
print("Names changed:", artistclean.sum())

# %%
pd.DataFrame({
    "Before": data["track_metadata.artist_name"],
    "After": clean["track_metadata.artist_name"]
}).head()

# %%
clean["track_metadata.track_name"] = data["track_metadata.track_name"].str.strip()

songclean = data["track_metadata.track_name"].notna() & (
    data["track_metadata.track_name"] != clean["track_metadata.track_name"]
)

# %%
pd.DataFrame({
    "Before": data["track_metadata.track_name"],
    "After": clean["track_metadata.track_name"]
}).head()

# %%
print("Songs changed:", songclean.sum())

# %%
record_text = pd.Series([
    json.dumps(record, sort_keys=True) for record in records
])

exact_duplicates = record_text.duplicated()
user_duplicates = data["user_id"].duplicated()
recording_duplicates = data["recording_msid"].duplicated()

event_duplicates = data.duplicated(
    subset=["user_id", "timestamp", "recording_msid"]
)

# %%
duplicate_counts = pd.Series({
    "Exact duplicate records": exact_duplicates.sum(),
    "Repeated user IDs": user_duplicates.sum(),
    "Repeated recording IDs": recording_duplicates.sum(),
    "Repeated event keys": event_duplicates.sum()
})

display(duplicate_counts)

# %%


# %%
missing_before = data.isna().sum()
missing_after = clean[data.columns].isna().sum()

missing_counts = pd.DataFrame({
    "Before": missing_before,
    "After": missing_after
})

display(missing_counts)

# %%
affected = missing_counts[
    (missing_counts["Before"] > 0) | (missing_counts["After"] > 0)
]

print(affected.to_string())

# %%
future_dates = clean["listen_datetime"] > pd.to_datetime(
    "2026-09-29", utc=True
)

bad_duration = clean["track_metadata.additional_info.duration"] <= 0
bad_duration_ms = clean["track_metadata.additional_info.duration_ms"] <= 0

blank_artists = clean["track_metadata.artist_name"] == ""
blank_songs = clean["track_metadata.track_name"] == ""

checks = pd.Series({
    "Missing or invalid dates": clean["listen_datetime"].isna().sum(),
    "Dates after dump date": future_dates.sum(),
    "Duration zero or less": bad_duration.sum(),
    "Duration_ms zero or less": bad_duration_ms.sum(),
    "Blank artist names": blank_artists.sum(),
    "Blank song titles": blank_songs.sum()
})

display(checks)

# %%
display(pd.DataFrame({
    "Original": [
        len(data),
        data["user_id"].nunique(),
        len(data)
    ],
    "Cleaned": [
        len(clean),
        clean["user_id"].nunique(),
        len(clean)
    ]
}, index=["Rows", "Unique listeners", "Streams"]))

# %%
display(pd.Series({"Original rows": len(data), "Cleaned rows": len(clean)}))

# %%
recent = clean[clean["listen_datetime"] > clean["listen_datetime"].max() - pd.Timedelta(days=28)]
display(recent.groupby("track_metadata.artist_name")["user_id"].nunique().sort_values(ascending=False).head(10))

# %%
display(data["track_metadata.additional_info.date"].dropna().head(10))

# %%
display(data.loc[
    data["track_metadata.additional_info.date"].notna(),
    ["track_metadata.artist_name",
     "track_metadata.release_name",
     "track_metadata.additional_info.date"]
].head(10))

# %%
sample = pd.concat([
    clean[clean["track_metadata.additional_info.date"].notna()].head(10),
    clean[clean["track_metadata.release_name"].isna()].head(10),
    clean[clean["track_metadata.additional_info.duration"].isna()].head(10),
    clean.head(50)
])

sample = sample.loc[~sample.index.duplicated()].head(50)
sample.to_csv("cleaned_50_jay.csv", index=False)

display(len(sample))
display(sample[["track_metadata.artist_name",
                "track_metadata.track_name",
                "listen_datetime"]].head())


