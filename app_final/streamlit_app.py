"""V3 Emerging Artist Exposure dashboard."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRESH_BUILD = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(FRESH_BUILD))

import streamlit as st
from app_final.data import load_data

st.set_page_config(
    page_title="Emerging Artist Exposure V3",
    layout="wide",
)

st.title("Emerging Artist Exposure")
st.caption(
    "V3 · Matched-listener audience momentum · "
    "September 28 vs. October 27, 2026 (UTC)"
)

try:
    ctx = load_data()
except (OSError, ValueError, KeyError) as exc:
    st.error(f"Unable to load V3 data: {exc}")
    st.stop()

st.info(
    "Rankings reflect observed listening activity among users present "
    "in both snapshots, not population-wide artist growth."
)

from app_final.views import shortlist, artist, segments, notes

tabs = st.tabs([
    "Shortlist",
    "Artist Detail",
    "Listener Insights",
    "Data Notes",
])

for tab, view in zip(
    tabs,
    [shortlist, artist, segments, notes],
):
    with tab:
        view.render(ctx)
