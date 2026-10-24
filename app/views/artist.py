import pandas as pd
import plotly.express as px
import streamlit as st
from analysis.segments import summarize_segments
from app.fmt import count, rate, growth, display_table


def picker_change():
    st.session_state['selected_artist'] = st.session_state['artist_picker']


def compare_change():
    st.session_state['compare_artists'] = list(st.session_state['artist_compare'])


def segment_bars(frame, evidence):
    # Kept local so views do not import one another.
    data = frame.copy()
    data['height'] = data.return_rate.where(data.eligible_new_listeners.ge(evidence), 0).fillna(0)
    data['label'] = [f'{rate(r.return_rate)} (n = {count(r.eligible_new_listeners)})'
                     if r.eligible_new_listeners >= evidence else f'too few (n = {count(r.eligible_new_listeners)})'
                     for r in data.itertuples()]
    fig = px.bar(data, x='segment', y='height', text='label', labels={'segment': 'Listener segment', 'height': 'Return rate'})
    fig.update_traces(textposition='outside', cliponaxis=False)
    fig.update_yaxes(tickformat='.0%', range=[0, max(0.15, data.height.max() * 1.3)])
    st.plotly_chart(fig)


def render(ctx):
    artists = ctx.scored.sort_values(['window_listeners', 'artist_name'], ascending=[False, True])
    if artists.empty:
        st.info('No stored artists in this population.')
        return
    keys = artists.artist_key.tolist()
    indexed = artists.set_index('artist_key')
    selected = st.session_state.get('selected_artist')
    fallback = ctx.shortlist.iloc[0].artist_key if len(ctx.shortlist) else keys[0]
    selected = selected if selected in keys else fallback
    st.session_state['artist_picker'] = selected
    key = st.selectbox('Artist', keys, format_func=lambda k: f'{indexed.loc[k, "artist_name"]} ({count(indexed.loc[k, "window_listeners"])})',
                       key='artist_picker', on_change=picker_change)
    row = indexed.loc[key]
    st.subheader(row.artist_name)
    badge = ('Shortlisted' if row.shortlisted else 'Candidate (single-fan risk, excluded)' if row.status == 'candidate'
             else {'insufficient_evidence': 'Insufficient evidence', 'established': 'Established', 'below_floor': 'Below floor'}[row.status])
    st.badge(badge, color='green' if row.shortlisted else 'orange')
    if row.shortlisted:
        st.caption(f'Rank {int(row["rank"])} of {len(ctx.shortlist):,}, score {row.exposure_score:.1f}')
    if pd.notna(row.primary_artist_mbid) and row.primary_artist_mbid:
        st.link_button('MusicBrainz artist', f'https://musicbrainz.org/artist/{row.primary_artist_mbid}')
    st.caption(f'First observed in data {pd.Timestamp(row.first_seen_day):%Y-%m-%d}')
    metrics = ['window_listeners', 'new_listeners', 'return_rate', 'repeat_listener_rate', 'growth_ratio', 'top_listener_share']
    values = [count(row.window_listeners), count(row.new_listeners), rate(row.return_rate), rate(row.repeat_listener_rate), growth(row.growth_ratio), rate(row.top_listener_share)]
    for tile, label, value in zip(st.columns(6), ['Listeners', 'New listeners', f'Return rate (n = {count(row.eligible_new_listeners)})', 'Repeat rate', 'Growth', 'Top-listener share'], values):
        tile.metric(label, value)
    if row.single_fan_risk:
        st.error(f'Single-fan risk: top listener has {rate(row.top_listener_share)} of listens.')
    weekly = ctx.tables['artist_weekly']
    own = weekly.loc[weekly.artist_key.eq(key)].sort_values('week_start')
    st.subheader('Weekly audience')
    fig = px.line(own, x='week_start', y=['listeners', 'new_listeners'], markers=True,
                  labels={'value': 'Listeners', 'week_start': 'Week starting', 'variable': 'Audience'})
    fig.update_xaxes(tickvals=own.week_start, tickformat='%b %-d')
    st.plotly_chart(fig)
    saved = [k for k in st.session_state.get('compare_artists', []) if k in keys and k != key][:3]
    st.session_state['compare_artists'] = saved
    st.session_state['artist_compare'] = saved
    others = st.multiselect('Compare up to 3 more artists', [k for k in keys if k != key],
                            format_func=lambda k: indexed.loc[k, 'artist_name'], max_selections=3,
                            key='artist_compare', on_change=compare_change)
    comparison = [key, *others]
    trend = weekly.loc[weekly.artist_key.isin(comparison)].merge(artists[['artist_key', 'artist_name']], on='artist_key')
    fig = px.line(trend.sort_values('week_start'), x='week_start', y='new_listeners', color='artist_name', markers=True,
                  labels={'new_listeners': 'New listeners', 'week_start': 'Week starting', 'artist_name': 'Artist'})
    fig.update_xaxes(tickvals=own.week_start, tickformat='%b %-d')
    st.plotly_chart(fig)
    st.dataframe(display_table(indexed.loc[comparison].reset_index()[['artist_name', *metrics]]), hide_index=True, width='stretch')
    st.subheader('Entry tracks')
    entries = ctx.tables['entry_tracks']
    entries = entries.loc[entries.artist_key.eq(key)].sort_values(['new_listeners', 'entry_track_name'], ascending=[False, True]).head(10).copy()
    entries['Return rate'] = [rate(r.return_rate) if r.eligible_new_listeners >= ctx.params.min_eligible_new else 'too few' for r in entries.itertuples()]
    entry_display = display_table(entries[['entry_track_name', 'new_listeners', 'eligible_new_listeners', 'returned_new_listeners', 'Return rate']]).rename(columns={'entry_track_name': 'Track', 'Eligible n': 'Eligible', 'returned_new_listeners': 'Returned'})
    st.dataframe(entry_display, hide_index=True, width='stretch')
    st.caption('First track each new listener played, and whether they came back within 7 days. Listeners with an unknown first track are omitted.')
    st.subheader('Return by listener segment')
    segment_bars(summarize_segments(ctx.tables['artist_segments'], [key]), ctx.params.min_eligible_new)
