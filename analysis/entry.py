"""Entry tracks: which track new listeners heard first, and whether they returned."""

from __future__ import annotations

import pandas as pd

ENTRY_COLUMNS = ["artist_key", "entry_track_key", "entry_track_name", "new_listeners",
                 "eligible_new_listeners", "returned_new_listeners", "return_rate"]


def entry_tracks(pairs: pd.DataFrame, min_new_listeners: int = 1) -> pd.DataFrame:
    """One row per (artist, entry track) over listeners discovered in the window.

    The display name is the most common entry_track_name for that key.
    Sorted by artist, then new_listeners descending, then track key.
    """
    new = pairs.loc[pairs["discovered_in_window"] & pairs["entry_track_key"].notna()].copy()
    if new.empty:
        return pd.DataFrame(columns=ENTRY_COLUMNS)
    new["returned_eligible"] = new["returned"] & new["eligible"]
    keys = ["artist_key", "entry_track_key"]
    out = new.groupby(keys).agg(
        new_listeners=("user_id", "size"),
        eligible_new_listeners=("eligible", "sum"),
        returned_new_listeners=("returned_eligible", "sum"),
    ).reset_index()
    names = (
        new.groupby(keys + ["entry_track_name"]).size().rename("n").reset_index()
        .sort_values(keys + ["n", "entry_track_name"], ascending=[True, True, False, True])
        .drop_duplicates(keys)[keys + ["entry_track_name"]]
    )
    out = out.merge(names, on=keys, how="left")
    eligible = out["eligible_new_listeners"].where(out["eligible_new_listeners"] > 0)
    out["return_rate"] = (out["returned_new_listeners"] / eligible).astype("float64")
    out = out.loc[out["new_listeners"] >= min_new_listeners]
    out = out.sort_values(["artist_key", "new_listeners", "entry_track_key"],
                          ascending=[True, False, True], kind="stable")
    for col in ["new_listeners", "eligible_new_listeners", "returned_new_listeners"]:
        out[col] = out[col].astype("int64")
    return out[ENTRY_COLUMNS].reset_index(drop=True)
