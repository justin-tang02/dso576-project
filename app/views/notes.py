import pandas as pd
import plotly.express as px
import streamlit as st
from app.fmt import rate, count


def render(ctx):
    st.subheader('Coverage and evidence')
    daily = ctx.tables['daily_coverage'].copy()
    daily['listen_day'] = pd.to_datetime(daily.listen_day)
    cfg = ctx.manifest['analysis_config']
    fig = px.bar(daily, x='listen_day', y='listens', labels={'listen_day': 'UTC day', 'listens': 'Listens'})
    fig.add_shape(type='rect', x0=cfg['window_start'],
                  x1=(pd.Timestamp(cfg['window_end']) + pd.Timedelta(days=1)).isoformat(),
                  y0=0, y1=1, xref='x', yref='paper',
                  fillcolor='gray', opacity=0.15, line_width=0, layer='below')
    st.plotly_chart(fig)
    st.caption('60 days through the window end; all users. Gray band marks the analysis window.')
    q = ctx.manifest['data_quality']
    facts = [('Listen range (UTC)', f"{q['first_listen_utc']} to {q['last_listen_utc']}"),
             ('Total listens', count(q['total_listens'])), ('Window listens', count(q['window_listens'])),
             ('Window share', rate(q['window_share'], 1)), ('Window listeners', count(q['window_listeners'])),
             ('Window artists', count(q['window_artists'])), ('Artist MBID share', rate(q['window_mbid_share'], 1)),
             ('Window listens from flagged heavy users', rate(q['window_heavy_user_listen_share'], 1)),
             ('Flagged heavy users in window', count(q['window_heavy_users'])),
             ('Multi-day listener share', rate(q['multi_day_listener_share'], 1)),
             ('Retention sufficiency (threshold 20%)', 'Pass' if q['retention_sufficient'] else 'Fail'),
             ('Last eligible discovery day', q['last_eligible_discovery'])]
    st.dataframe(pd.DataFrame(facts, columns=['Fact', 'Value']), hide_index=True, width='stretch')
    percentiles = [(label, count(q[field])) for label, field in [
        ('p50', 'artist_listeners_p50'), ('p90', 'artist_listeners_p90'),
        ('p99', 'artist_listeners_p99'), ('max', 'artist_listeners_max')]]
    st.dataframe(pd.DataFrame(percentiles, columns=['Listener percentile', 'Listeners']), hide_index=True)
    st.caption('Over stored artists (2+ listeners), all users.')
    st.subheader('Definitions')
    definitions = [
        ('Listen', 'One cleaned row of the dump.'),
        ('Window', f"{cfg['window_start']} to {cfg['window_end']} inclusive, UTC. Other rows count only as history."),
        ('Early / late', 'Days 1–14 / 15–28 of the window.'),
        ('Artist', 'Whitespace-collapsed, NFKC, casefolded credit string. Collaborations are one entity; various artists and unknown are excluded. Most common raw name is displayed; MBID only adds a link.'),
        ('Population', 'All listeners, or exclude users flagged above the 99.5th percentile of whole-dump listens. Daily coverage always includes all users.'),
        ('Listener', 'A user with at least one window listen of the artist.'),
        ('New listener', 'First observed artist listen in all cleaned history is in the window; not proven discovery.'),
        ('Eligible new listener', f"First day on or before {q['last_eligible_discovery']}, allowing 7 follow-up days."),
        ('Returned', 'Eligible listener played the artist again 1–7 days after their first day.'),
        ('Repeat rate', 'Share of window listeners active on at least two different days.'),
        ('Growth', '(Late listeners + 1) / (early listeners + 1); above 1 means growing.'),
        ('Segment', 'Window listens across artists: light <50, moderate 50–499, heavy 500+. Heavy segment differs from flagged heavy users.'),
        ('Stored artist', 'At least 2 window listeners. Funnel counts omit artists with one listener.'),
        ('Status', 'First matching rule: below listener floor, above established ceiling, insufficient eligible new listeners, otherwise candidate.'),
        ('Shortlisted', 'Candidate, excluding single-fan risk when that filter is enabled.'),
        ('Single-fan risk', 'Top listener contributes more than 50% of artist listens.'),
        ('Exposure score', 'Weighted average of component percentiles within the current shortlist; changes with filters and weights.')]
    st.dataframe(pd.DataFrame(definitions, columns=['Term', 'Definition']), hide_index=True, width='stretch')
    st.subheader('Limits')
    st.write('ListenBrainz users are not a random sample of streaming listeners. First observed listen is not true discovery. Name keys can merge namesakes. Findings are associations only, not the effect of exposure.')
