from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.config import ScoringParams
from analysis.scoring import score_artists
from app.controls import sidebar_controls
from app.data import load_data
from app.views import shortlist, artist, segments, notes

st.set_page_config(page_title="Emerging Artist Exposure", layout="wide")

@dataclass
class Context:
    tables: dict
    population: str
    params: ScoringParams
    scored: pd.DataFrame
    manifest: dict
    evidence_min: int


tables, manifest = load_data()
population, params = sidebar_controls()
pop_tables = {name: (table.loc[table.population == population].drop(columns="population").reset_index(drop=True)
                     if "population" in table.columns else table.copy()) for name, table in tables.items()}
metrics = pop_tables["artist_metrics"]
try:
    scored = score_artists(metrics, params)
except ValueError as exc:
    st.error(str(exc))
    st.stop()
ctx = Context(pop_tables, population, params, scored, manifest, params.min_eligible_new)

st.title("Emerging Artist Exposure")
try:
    built = datetime.fromisoformat(manifest["generated_at_utc"].replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M UTC")
except (KeyError, ValueError):
    built = str(manifest.get("generated_at_utc", "unknown"))
st.caption(f"Window: Sep 1 to Sep 28, 2026 (UTC) | Population: {'All listeners' if population == 'all' else 'Exclude heavy users'} | Data built {built}")
if manifest.get("is_demo"):
    st.warning("Synthetic demo data. Artists are invented; do not use for decisions.")
if not manifest.get("data_quality", {}).get("retention_sufficient", True):
    st.error("Few listeners were active on 2+ days in this window, so return and repeat rates are unreliable. See Data Notes.")

short_tab, artist_tab, segment_tab, notes_tab = st.tabs(["Shortlist", "Artist Detail", "Listener Segments", "Data Notes"])
with short_tab: shortlist.render(ctx)
with artist_tab: artist.render(ctx)
with segment_tab: segments.render(ctx)
with notes_tab: notes.render(ctx)
