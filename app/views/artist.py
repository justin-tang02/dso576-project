import pandas as pd
import plotly.express as px
import streamlit as st

from analysis.segments import summarize_segments
from app.fmt import count, rate, growth, score

METRICS = [("Listeners", "window_listeners"), ("New listeners", "new_listeners"),
           ("Return rate", "return_rate"), ("Repeat rate", "repeat_listener_rate"),
           ("Growth", "growth_ratio"), ("Top-listener share", "top_listener_share")]

def _artist_changed():
    st.session_state["selected_artist"] = st.session_state["artist_picker"]


def _weekly(ctx, keys):
    weekly = ctx.tables["artist_weekly"].loc[ctx.tables["artist_weekly"].artist_key.isin(keys)].copy()
    names = ctx.tables["artist_metrics"].set_index("artist_key").artist_name.to_dict()
    weekly["Artist"] = weekly.artist_key.map(names)
    weekly["Week"] = pd.to_datetime(weekly.week_start).dt.strftime("%b %-d")
    return weekly


def render(ctx):
    metrics = ctx.tables["artist_metrics"]
    scored = ctx.scored.set_index("artist_key", drop=False)
    if metrics.empty:
        st.info("No stored artists are available for this population.")
        return
    options = metrics.sort_values(["window_listeners", "artist_name"], ascending=[False, True], kind="stable")
    labels = {r.artist_key: f"{r.artist_name} ({count(r.window_listeners)})" for r in options.itertuples()}
    keys = options.artist_key.tolist()
    current = st.session_state.get("selected_artist")
    if current not in keys:
        ranked = ctx.scored.loc[ctx.scored.shortlisted].sort_values("rank")
        current = ranked.iloc[0].artist_key if len(ranked) else options.iloc[0].artist_key
    if "artist_picker" not in st.session_state or st.session_state["artist_picker"] not in keys:
        st.session_state["artist_picker"] = current
    picked = st.selectbox("Artist", keys, format_func=lambda k: labels[k], key="artist_picker", on_change=_artist_changed)
    compare = [k for k in st.session_state.get("compare_artists", []) if k in keys and k != picked][:3]
    st.session_state["compare_artists"] = compare
    row = scored.loc[picked]
    name = row.artist_name
    if bool(row.shortlisted): badge = "Shortlisted"
    elif row.status == "candidate": badge = "Candidate (single-fan risk, excluded)"
    else: badge = {"insufficient_evidence":"Insufficient evidence","established":"Established","below_floor":"Below floor"}[row.status]
    st.subheader(name)
    st.badge(badge)
    if bool(row.shortlisted): st.caption(f"Rank {int(row['rank'])} of {int(ctx.scored.shortlisted.sum())}, score {score(row.exposure_score)}")
    mbid = str(row.primary_artist_mbid or "").strip()
    if mbid and mbid.lower() != "nan": st.markdown(f"[MusicBrainz artist page](https://musicbrainz.org/artist/{mbid})")
    st.caption(f"First observed in data {pd.to_datetime(row.first_seen_day).strftime('%Y-%m-%d')}")
    tiles = st.columns(6)
    for col, (label, field) in zip(tiles, METRICS):
        value = row[field]
        display = count(value) if field in ("window_listeners", "new_listeners") else growth(value) if field == "growth_ratio" else rate(value)
        col.metric(label, display, help=f"n = {count(row.eligible_new_listeners)}" if field == "return_rate" else None)
    if bool(row.single_fan_risk): st.warning("Top-listener share indicates single-fan risk.")
    weekly = _weekly(ctx, [picked])
    fig = px.line(weekly, x="Week", y=["listeners", "new_listeners"], markers=True,
                  labels={"value":"Listeners", "variable":"Series"}, title="Weekly listeners and new listeners")
    st.plotly_chart(fig, use_container_width=True)
    entries = ctx.tables["entry_tracks"].loc[ctx.tables["entry_tracks"].artist_key.eq(picked)].sort_values("new_listeners", ascending=False).head(10).copy()
    entries["Return rate"] = entries.apply(lambda x: rate(x.return_rate) if x.eligible_new_listeners >= ctx.evidence_min else "too few", axis=1)
    entries = entries.rename(columns={"entry_track_name":"Track","new_listeners":"New listeners","eligible_new_listeners":"Eligible","returned_new_listeners":"Returned"})
    st.markdown("**Entry tracks**")
    st.caption("First track each new listener played, and whether they came back within 7 days. Listeners with an unknown first track are omitted.")
    st.dataframe(entries[["Track","New listeners","Eligible","Returned","Return rate"]], hide_index=True, use_container_width=True)
    st.markdown("**Return by listener segment**")
    summary = summarize_segments(ctx.tables["artist_segments"], [picked])
    import plotly.graph_objects as go
    y = [r if n >= ctx.evidence_min else 0 for r, n in zip(summary.return_rate, summary.eligible_new_listeners)]
    labels = [rate(r) if n >= ctx.evidence_min else f"too few (n = {count(n)})"
              for r, n in zip(summary.return_rate, summary.eligible_new_listeners)]
    fig = go.Figure(go.Bar(x=summary.segment, y=y, text=labels, textposition="outside",
                           customdata=summary.eligible_new_listeners,
                           hovertemplate="%{x}: %{y:.1%}<br>Eligible n=%{customdata}<extra></extra>"))
    fig.update_layout(yaxis_tickformat=".0%", yaxis_title="Return rate", xaxis_title="Segment", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    candidate_options = [k for k in keys if k != picked]
    chosen = st.multiselect("Compare artists (up to 3)", candidate_options, default=compare,
                            format_func=lambda k: labels[k], max_selections=3, key="compare_picker")
    st.session_state["compare_artists"] = chosen
    comp_keys = [picked, *chosen]
    if chosen:
        comp_week = _weekly(ctx, comp_keys)
        fig = px.line(comp_week, x="Week", y="new_listeners", color="Artist", markers=True,
                      title="New listeners per week", labels={"new_listeners":"New listeners"})
        st.plotly_chart(fig, use_container_width=True)
        comp = scored.loc[comp_keys, ["artist_name", *[field for _, field in METRICS]]].copy().rename(columns={"artist_name":"Artist"})
        comp.insert(0, "Artist", comp.pop("Artist"))
        comp.columns = ["Artist", *[label for label, _ in METRICS]]
        for col in ["Return rate","Repeat rate","Top-listener share"]: comp[col] = comp[col].map(rate)
        comp["Growth"] = comp.Growth.map(growth)
        st.dataframe(comp, hide_index=True, use_container_width=True)
