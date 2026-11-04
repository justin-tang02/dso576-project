import plotly.graph_objects as go
import streamlit as st

from analysis.segments import summarize_segments
from app.fmt import count, rate


def render(ctx):
    users = ctx.tables["segment_users"].copy()
    users["Share of listens"] = users.share_of_listens.map(lambda x: rate(x, 1))
    users = users.rename(columns={"segment":"Segment","users":"Users","window_listens":"Window listens"})
    st.dataframe(users[["Segment","Users","Window listens","Share of listens"]], hide_index=True, use_container_width=True)
    keys = ctx.scored.loc[ctx.scored.shortlisted, "artist_key"].tolist()
    short = summarize_segments(ctx.tables["artist_segments"], keys)
    all_artists = summarize_segments(ctx.tables["artist_segments"])
    fig = go.Figure()
    for label, table in [("Current shortlist", short), ("All stored artists", all_artists)]:
        y = [r if n >= ctx.evidence_min else 0 for r, n in zip(table.return_rate, table.eligible_new_listeners)]
        fig.add_bar(name=label, x=table.segment, y=y, text=[rate(r) if n >= ctx.evidence_min else "too few" for r,n in zip(table.return_rate,table.eligible_new_listeners)],
                    customdata=table.eligible_new_listeners, hovertemplate="%{x}: %{y:.1%}<br>Eligible n=%{customdata}<extra>%{fullData.name}</extra>")
    fig.update_layout(barmode="group", yaxis_tickformat=".0%", yaxis_title="Return rate", xaxis_title="Segment")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Bars below the evidence minimum are labeled too few.")
    st.markdown("**Shortlist counts by segment**")
    out = short.rename(columns={"artists":"Artists","window_listeners":"Listener-artist pairs","new_listeners":"New","eligible_new_listeners":"Eligible","returned_new_listeners":"Returned"})
    out = out[["segment","Artists","Listener-artist pairs","New","Eligible","Returned"]].rename(columns={"segment":"Segment"})
    st.dataframe(out, hide_index=True, use_container_width=True)
    st.caption("Aim exposure at the segment with the highest shortlist return rate, and check it beats the all-artist baseline.")
