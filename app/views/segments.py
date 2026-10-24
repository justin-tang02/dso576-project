import pandas as pd
import plotly.express as px
import streamlit as st
from analysis.segments import summarize_segments
from app.fmt import display_table, rate, count


def return_chart(frame, evidence, group=None):
    data = frame.copy()
    enough = data.eligible_new_listeners.ge(evidence)
    data['shown_rate'] = data.return_rate.where(enough)
    data['label'] = [f'{rate(r.return_rate)} (n = {count(r.eligible_new_listeners)})' if ok
                     else f'too few (n = {count(r.eligible_new_listeners)})'
                     for (_, r), ok in zip(data.iterrows(), enough)]
    # Zero-height placeholders place low-evidence labels without drawing a rate bar.
    data['shown_rate'] = data.shown_rate.fillna(0)
    fig = px.bar(data, x='segment', y='shown_rate', color=group, barmode='group', text='label',
                 labels={'segment': 'Listener segment', 'shown_rate': 'Return rate'},
                 category_orders={'segment': ['light', 'moderate', 'heavy']})
    fig.update_traces(textposition='outside', cliponaxis=False)
    fig.update_yaxes(tickformat='.0%', range=[0, max(0.15, data.shown_rate.max() * 1.3)])
    fig.update_layout(margin=dict(t=40))
    st.plotly_chart(fig)


def render(ctx):
    st.subheader('Who comes back after a first observed listen?')
    users = display_table(ctx.tables['segment_users']).rename(columns={
        'segment': 'Segment', 'users': 'Users', 'window_listens': 'Window listens', 'share_of_listens': 'Share of listens'})
    st.dataframe(users, hide_index=True, width='stretch')
    selected = summarize_segments(ctx.tables['artist_segments'], ctx.shortlist.artist_key)
    baseline = summarize_segments(ctx.tables['artist_segments'])
    return_chart(pd.concat([selected.assign(Group='Current shortlist'), baseline.assign(Group='All stored artists')]), ctx.params.min_eligible_new, 'Group')
    st.subheader('Shortlist evidence by segment')
    st.dataframe(display_table(selected.drop(columns='return_rate')).rename(columns={
        'segment': 'Segment', 'artists': 'Artists', 'Listeners': 'Listener-artist pairs',
        'returned_new_listeners': 'Returned'}), hide_index=True, width='stretch')
    st.caption('A person counts once per artist in listener-artist pairs.')
    st.caption('Aim exposure at the segment with the highest shortlist return rate, and check it beats the all-artist baseline.')
