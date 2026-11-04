from __future__ import annotations

import os
from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.config import DEMO_DIR, PROJECT_DIR
from analysis.store import read_aggregates


def resolve_data_dir() -> Path:
    configured = os.environ.get("EAE_DATA_DIR")
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else PROJECT_DIR / path
    normal = PROJECT_DIR / "data" / "aggregates"
    demo = DEMO_DIR / "aggregates"
    if (normal / "manifest.json").exists():
        return normal
    return demo


@st.cache_data(show_spinner="Loading aggregate data…")
def load_aggregates(folder: str, generated_at: str):
    return read_aggregates(Path(folder))


def load_data():
    folder = resolve_data_dir()
    manifest_path = folder / "manifest.json"
    if not manifest_path.exists():
        st.error(f"No manifest.json found in {folder}. Check EAE_DATA_DIR or build the aggregates.")
        st.stop()
    import json
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tables, manifest = load_aggregates(str(folder), manifest.get("generated_at_utc", ""))
    return tables, manifest
