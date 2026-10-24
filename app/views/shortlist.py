import math
import plotly.express as px
import streamlit as st
from analysis.scoring import status_counts
from app.fmt import count, rate, growth, display_table

EXPORT_COLUMNS = ['rank', 'artist_key', 'artist_name', 'exposure_score', 'new_listeners',
                  'return_rate', 'eligible_new_listeners', 'repeat_listener_rate', 'growth_ratio',
                  'window_listeners', 'top_listener_share', 'primary_artist_mbid']


def select_table(rows, artist_keys):
    if rows and rows[0] < len(artist_keys):
        st.session_state['selected_artist'] = artist_keys[rows[0]]


def select_scatter(points):
    if points and points[0].get('customdata'):
        st.session_state['selected_artist'] = points[0]['customdata'][0]


def table_callback(keys):
    select_table(st.session_state['shortlist_table'].selection.rows, keys)


def scatter_callback():
    select_scatter(st.session_state['shortlist_scatter'].selection.points)


def render(ctx):
    pool = ctx.shortlist
    tiles = st.columns(4)
    tiles[0].metric('Shortlisted artists', count(len(pool)))
    tiles[1].metric('Active listeners in population', count(ctx.tables['segment_users'].users.sum()))
    tiles[2].metric('Median return rate', rate(pool.return_rate.median()))
    tiles[3].metric('Median growth', growth(pool.growth_ratio.median()))
    counts = status_counts(ctx.scored).set_index('status').artists
    risk = int((ctx.scored.status.eq('candidate') & ctx.scored.single_fan_risk).sum())
    st.caption(f"{counts['candidate']:,} candidates, {counts['insufficient_evidence']:,} insufficient evidence, {counts['established']:,} established, {counts['below_floor']:,} below floor; {risk:,} single-fan risk " + ('removed' if ctx.params.exclude_single_fan else 'kept (filter off)'))
    if pool.empty:
        st.info('No artists meet these settings. Widen the listener band or lower the evidence minimum.')
    else:
        scatter = pool.copy()
        scatter['log_growth'] = scatter.growth_ratio.map(math.log2)
        limit = max(1, scatter.log_growth.abs().max())
        fig = px.scatter(scatter, x='new_listeners', y='return_rate', size='window_listeners',
                         color='log_growth', color_continuous_scale=['#ba4b50', '#d7d9dd', '#377eb8'],
                         range_color=[-limit, limit], log_x=True, hover_name='artist_name',
                         custom_data=['artist_key'], hover_data={'exposure_score': ':.1f', 'rank': True,
                         'new_listeners': True, 'return_rate': ':.0%', 'repeat_listener_rate': ':.0%',
                         'growth_ratio': ':.2f', 'log_growth': False},
                         labels={'new_listeners': 'New listeners', 'return_rate': 'Return rate'})
        ticks = list(range(math.ceil(-limit), math.floor(limit) + 1))
        fig.update_layout(coloraxis_colorbar=dict(title='Growth', tickvals=ticks,
                          ticktext=[growth(2 ** x) for x in ticks]), margin=dict(t=20, b=20))
        fig.update_yaxes(tickformat='.0%')
        st.plotly_chart(fig, key='shortlist_scatter', on_select=scatter_callback, selection_mode='points')
    search = st.text_input('Search shortlist', key='shortlist_search')
    shown = pool.loc[pool.artist_name.str.contains(search, case=False, regex=False, na=False)].head(50)
    st.dataframe(display_table(shown[[c for c in EXPORT_COLUMNS if c != 'artist_key']]),
                 hide_index=True, width='stretch', key='shortlist_table', selection_mode='single-row',
                 on_select=lambda: table_callback(shown.artist_key.tolist()))
    selected = st.session_state.get('selected_artist')
    match = ctx.scored.loc[ctx.scored.artist_key.eq(selected)]
    if not match.empty:
        st.caption(f'Selected {match.iloc[0].artist_name}. Open the Artist Detail tab.')
    st.download_button('Download full shortlist', pool[EXPORT_COLUMNS].to_csv(index=False),
                       file_name=f'shortlist_{ctx.population}.csv', mime='text/csv')
    with st.expander("Why isn't an artist here?"):
        excluded = ctx.scored.loc[~ctx.scored.shortlisted].sort_values(['window_listeners', 'artist_name'], ascending=[False, True]).copy()
        query = st.text_input('Search excluded artists', key='shortlist_excluded_search')
        excluded = excluded.loc[excluded.artist_name.str.contains(query, case=False, regex=False, na=False)]
        def reason(row):
            if row.status == 'below_floor':
                return f'Fewer than {ctx.params.min_listeners} listeners'
            if row.status == 'established':
                return f'More than {ctx.params.max_listeners} listeners'
            if row.status == 'insufficient_evidence':
                return f'Only {row.eligible_new_listeners} eligible new listeners (need {ctx.params.min_eligible_new})'
            return f'Top listener has {rate(row.top_listener_share)} of listens'
        excluded['Reason'] = excluded.apply(reason, axis=1)
        st.dataframe(display_table(excluded[['artist_name', 'window_listeners', 'eligible_new_listeners', 'top_listener_share', 'Reason']]), hide_index=True, width='stretch')
        st.caption('Artists with one listener are not stored.')
