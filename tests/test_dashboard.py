"""Demo acceptance checks. These read only the prebuilt aggregate tables."""
from io import StringIO
from pathlib import Path
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from analysis.config import DEMO_DIR, ScoringParams
from analysis.scoring import score_artists, shortlist
from analysis.segments import summarize_segments
from analysis.store import read_aggregates
from app.views.shortlist import EXPORT_COLUMNS

ROOT = Path(__file__).resolve().parents[1]


def assert_healthy(app):
    assert not app.exception, [e.message for e in app.exception]


def test_demo_controls(monkeypatch):
    monkeypatch.setenv('EAE_DATA_DIR', 'data/demo/aggregates')
    app = AppTest.from_file(str(ROOT / 'app/streamlit_app.py')).run(timeout=60)
    assert_healthy(app)
    assert app.metric[0].value == '945'
    first = app.dataframe[0].value.iloc[0]
    assert (first['Artist'], first['Score'], first['New listeners'], first['Return rate']) == ('Synthetic Artist 0131', '87.2', '42', '59%')
    assert any('1,070 candidates, 375 insufficient evidence, 13 established, 876 below floor; 125 single-fan risk removed' in c.value for c in app.caption)
    assert 'Synthetic demo data' in app.warning[0].value
    assert 'selected_artist' not in app.session_state
    app.radio(key='controls_population').set_value('Exclude heavy users').run()
    assert_healthy(app)
    assert app.metric[0].value == '771'
    assert app.dataframe[0].value.iloc[0]['Score'] == '88.7'
    assert app.dataframe[0].value.iloc[2]['Artist'] == 'Synthetic Artist 0178'
    app.radio(key='controls_population').set_value('All listeners').run()
    app.slider(key='controls_band').set_value((5, 1000)).run()
    assert int(app.metric[0].value.replace(',', '')) > 945
    assert any('0 established' in c.value for c in app.caption)
    before = app.dataframe[0].value.copy()
    before_count = int(app.metric[0].value.replace(',', ''))
    for name in ScoringParams().weights:
        app.slider(key=f'controls_{name}').set_value(0.0)
    app.run()
    assert app.error
    pd.testing.assert_frame_equal(before, app.dataframe[0].value)
    # Other filters still apply while all weights are zero.
    app.slider(key='controls_evidence').set_value(30).run()
    assert int(app.metric[0].value.replace(',', '')) < before_count
    app.text_input(key='shortlist_search').set_value('0131').run()
    app.button[0].click().run()
    assert_healthy(app)
    assert app.metric[0].value == '945'
    assert app.text_input(key='shortlist_search').value == '0131'
    assert app.slider(key='controls_band').value == (5, 200)
    # Empty shortlist must leave the detail and segment views usable.
    app.slider(key='controls_band').set_value((2, 2)).run()
    assert_healthy(app)
    assert app.metric[0].value == '0'
    assert any('No artists meet these settings' in item.value for item in app.info)


@pytest.mark.parametrize('mode', ['table', 'scatter'])
def test_selection_handlers(mode, monkeypatch):
    monkeypatch.setenv('EAE_DATA_DIR', 'data/demo/aggregates')
    source = f'''
import streamlit as st
from app.views.shortlist import select_table, select_scatter
select_table([0], ['synthetic artist 0131']) if {mode!r} == 'table' else select_scatter([{{'customdata': ['synthetic artist 0131']}}])
select_table([], [])
select_scatter([])
import runpy
runpy.run_path({str(ROOT / 'app/streamlit_app.py')!r}, run_name='__main__')
'''
    app = AppTest.from_string(source).run(timeout=60)
    assert_healthy(app)
    assert app.session_state['selected_artist'] == 'synthetic artist 0131'
    assert app.selectbox(key='artist_picker').value == 'synthetic artist 0131'
    assert any(s.value == 'Synthetic Artist 0131' for s in app.subheader)
    entry = next(d.value for d in app.dataframe if 'Track' in d.value.columns)
    assert entry.iloc[0].to_dict() == {'Track': 'Track 01', 'New listeners': '12', 'Eligible': '5', 'Returned': '3', 'Return rate': '60%'}


def test_demo_aggregates_and_download():
    tables, _ = read_aggregates(DEMO_DIR / 'aggregates')
    metrics = tables['artist_metrics'].query("population == 'all'")
    pool = shortlist(score_artists(metrics, ScoringParams()))
    exported = pd.read_csv(StringIO(pool[EXPORT_COLUMNS].to_csv(index=False)))
    assert len(exported) == 945
    assert exported.columns.tolist() == EXPORT_COLUMNS
    assert exported.iloc[0].return_rate == pytest.approx(16 / 27)
    weekly = tables['artist_weekly'].query("population == 'all' and artist_key == 'synthetic artist 0131'").sort_values('week_start')
    assert weekly.listeners.tolist() == [13, 19, 21, 33]
    assert weekly.new_listeners.tolist() == [11, 8, 8, 15]
    segment = summarize_segments(tables['artist_segments'].query("population == 'all'"), pool.artist_key)
    assert [round(v * 100) for v in segment.return_rate] == [23, 34, 52]


def test_missing_override(monkeypatch, tmp_path):
    monkeypatch.setenv('EAE_DATA_DIR', str(tmp_path))
    app = AppTest.from_file(str(ROOT / 'app/streamlit_app.py')).run(timeout=60)
    assert_healthy(app)
    assert 'No manifest.json' in app.error[0].value
    assert not app.metric


def test_real_manifest_banner_and_time(monkeypatch, tmp_path):
    import json
    import shutil
    for file in (DEMO_DIR / 'aggregates').iterdir():
        shutil.copy2(file, tmp_path / file.name)
    manifest = json.loads((tmp_path / 'manifest.json').read_text())
    manifest.update(is_demo=False, generated_at_utc='2026-10-22T12:34:00+00:00')
    manifest['data_quality']['retention_sufficient'] = False
    (tmp_path / 'manifest.json').write_text(json.dumps(manifest))
    monkeypatch.setenv('EAE_DATA_DIR', str(tmp_path))
    app = AppTest.from_file(str(ROOT / 'app/streamlit_app.py')).run(timeout=60)
    assert_healthy(app)
    assert not app.warning
    assert '2026-10-22 12:34 UTC' in app.caption[0].value
    assert 'Few listeners' in app.error[0].value
    facts = next(d.value for d in app.dataframe if 'Fact' in d.value.columns)
    assert facts.set_index('Fact').loc['Total listens', 'Value'] == '183,575'
