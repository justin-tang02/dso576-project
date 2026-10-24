from dataclasses import dataclass
import os
from pathlib import Path
import pandas as pd
import streamlit as st
from analysis.config import PROJECT_DIR, AGGREGATES_DIR, DEMO_DIR, ScoringParams
from analysis.store import read_aggregates, read_manifest


def data_folder():
    override = os.environ.get('EAE_DATA_DIR')
    if override is not None:
        folder = Path(override)
        if not folder.is_absolute():
            folder = PROJECT_DIR / folder
    else:
        folder = AGGREGATES_DIR if (AGGREGATES_DIR / 'manifest.json').exists() else DEMO_DIR / 'aggregates'
    if not (folder / 'manifest.json').is_file():
        raise ValueError(f'No manifest.json in aggregate folder: {folder}')
    return folder


@st.cache_data(show_spinner='Loading aggregate tables…')
def load_tables(folder: str, generated_at_utc: str):
    return read_aggregates(Path(folder))[0]


@dataclass
class Context:
    tables: dict[str, pd.DataFrame]
    scored: pd.DataFrame
    params: ScoringParams
    manifest: dict
    population: str

    @property
    def shortlist(self):
        return self.scored.loc[self.scored.shortlisted].sort_values('rank')
