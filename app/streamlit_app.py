from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st
from analysis.scoring import score_artists
from analysis.store import read_manifest
from app.data import Context, data_folder, load_tables
from app import controls
from app.views import shortlist, artist, segments, notes

st.set_page_config(page_title='Emerging Artist Exposure', page_icon='♫', layout='wide')
st.title('Emerging Artist Exposure')
try:
    folder = data_folder()
    manifest = read_manifest(folder)
    tables = load_tables(str(folder), manifest['generated_at_utc'])
except (OSError, ValueError, KeyError) as exc:
    st.error(f'Unable to load aggregates: {exc}')
    st.stop()

population, params = controls.render()
tables = {name: (table.loc[table.population.eq(population)].drop(columns='population').reset_index(drop=True)
                 if 'population' in table else table) for name, table in tables.items()}
ctx = Context(tables, score_artists(tables['artist_metrics'], params), params, manifest, population)
cfg = manifest['analysis_config']
start, end = pd.Timestamp(cfg['window_start']), pd.Timestamp(cfg['window_end'])
built = pd.Timestamp(manifest['generated_at_utc']).tz_convert('UTC').strftime('%Y-%m-%d %H:%M UTC')
st.caption(f"Window: {start.strftime('%b')} {start.day} to {end.strftime('%b')} {end.day}, {end.year} (UTC) | Population: {'All listeners' if population == 'all' else 'Exclude heavy users'} | Data built {built}")
if manifest.get('is_demo'):
    st.warning('Synthetic demo data. Artists are invented; do not use for decisions.')
if not manifest['data_quality']['retention_sufficient']:
    st.error('Few listeners were active on 2+ days in this window, so return and repeat rates are unreliable. See Data Notes.')
for tab, view in zip(st.tabs(['Shortlist', 'Artist Detail', 'Listener Segments', 'Data Notes']),
                     [shortlist, artist, segments, notes]):
    with tab:
        view.render(ctx)
