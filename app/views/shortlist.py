import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from analysis.scoring import shortlist as get_shortlist, status_counts
from app.fmt import count, rate, growth, score

CSV_COLUMNS = ["rank", "artist_key", "artist_name", "exposure_score", "new_listeners", "return_rate",
               "eligible_new_listeners", "repeat_listener_rate", "growth_ratio", "window_listeners",
               "top_listener_share", "primary_artist_mbid"]

def _selected_from_table():
    event = st.session_state.get("shortlist_table")
    rows = event.selection.rows if event is not None else []
    if rows:
        frame = st.session_state.get("_shortlist_display")
        if frame is not None and rows[0] < len(frame):
            st.session_state["selected_artist"] = frame.iloc[rows[0]].artist_key

def _selected_from_scatter():
    event = st.session_state.get("shortlist_scatter")
    points = event.selection.points if event is not None else []
    if points:
        custom = points[0].get("customdata") or []
        if custom:
            st.session_state["selected_artist"] = custom[0]


def render(ctx):
    scored = ctx.scored
    short = get_shortlist(scored)
    quality_users = ctx.tables["segment_users"]["users"].sum()
    a, b, c, d = st.columns(4)
    a.metric("Shortlisted artists", count(len(short)))
    b.metric("Active listeners in population", count(quality_users))
    c.metric("Median return rate", rate(short.return_rate.median() if len(short) else float("nan")))
    d.metric("Median growth", growth(short.growth_ratio.median() if len(short) else None))
    counts = status_counts(scored).set_index("status")["artists"]
    risk_n = int((scored.status.eq("candidate") & scored.single_fan_risk).sum())
    tail = f"{count(risk_n)} single-fan risk removed" if ctx.params.exclude_single_fan else f"{count(risk_n)} single-fan risk kept (filter off)"
    st.caption(f"{count(counts['candidate'])} candidates, {count(counts['insufficient_evidence'])} insufficient evidence, {count(counts['established'])} established, {count(counts['below_floor'])} below floor; {tail}")
    if short.empty:
        st.info("No artists meet these settings. Widen the listener band or lower the evidence minimum.")
        return
    key_to_name = short.set_index("artist_key").artist_name.to_dict()
    if st.session_state.get("selected_artist") in key_to_name:
        st.info(f"Selected {key_to_name[st.session_state['selected_artist']]}. Open the Artist Detail tab.")
    search = st.text_input("Search shortlist", key="shortlist_search")
    display = short.loc[short.artist_name.str.contains(search, case=False, na=False)].head(50).copy()
    display["Rank"] = display["rank"].astype(int)
    display = display.rename(columns={"artist_name":"Artist", "exposure_score":"Score", "new_listeners":"New listeners",
        "return_rate":"Return rate", "eligible_new_listeners":"Eligible n", "repeat_listener_rate":"Repeat rate",
        "growth_ratio":"Growth", "window_listeners":"Listeners", "top_listener_share":"Top-listener share",
        "primary_artist_mbid":"MBID"})
    display["MBID"] = display.MBID.fillna("").map(lambda x: "yes" if str(x).strip() else "no")
    cols = ["Rank", "Artist", "Score", "New listeners", "Return rate", "Eligible n", "Repeat rate", "Growth", "Listeners", "Top-listener share", "MBID"]
    shown = display[cols].copy()
    for col in ["Return rate", "Repeat rate", "Top-listener share"]: shown[col] = shown[col].map(rate)
    shown["Growth"] = shown.Growth.map(growth)
    shown["Score"] = shown.Score.map(score)
    st.session_state["_shortlist_display"] = display
    st.dataframe(shown, hide_index=True, on_select=_selected_from_table, selection_mode="single-row", use_container_width=True, key="shortlist_table")
    csv = short[CSV_COLUMNS].to_csv(index=False).encode("utf-8")
    st.download_button("Download shortlist CSV", csv, f"shortlist_{ctx.population}.csv", "text/csv")
    with st.expander("Why isn't an artist here?"):
        st.caption("Artists with one listener are not stored in the aggregates.")
        excluded = scored.loc[~scored.shortlisted].copy().sort_values(["window_listeners", "artist_name"], ascending=[False, True])
        q = st.text_input("Search excluded artists", key="excluded_search")
        excluded = excluded.loc[excluded.artist_name.str.contains(q, case=False, na=False)]
        def reason(row):
            if row.status == "below_floor": return f"Fewer than {ctx.params.min_listeners} listeners"
            if row.status == "established": return f"More than {ctx.params.max_listeners} listeners"
            if row.status == "insufficient_evidence": return f"Only {count(row.eligible_new_listeners)} eligible new listeners (need {ctx.params.min_eligible_new})"
            return f"Top listener has {rate(row.top_listener_share)} of listens"
        out = pd.DataFrame({"Artist":excluded.artist_name, "Listeners":excluded.window_listeners,
            "Eligible n":excluded.eligible_new_listeners, "Top-listener share":excluded.top_listener_share.map(rate),
            "Reason":excluded.apply(reason, axis=1)})
        st.dataframe(out, hide_index=True, use_container_width=True)
    plot = short.copy()
    plot["growth_color"] = np.log2(plot.growth_ratio.clip(lower=0.0001))
    fig = px.scatter(plot, x="new_listeners", y="return_rate", color="growth_color", size="window_listeners",
        custom_data=["artist_key"],
        hover_name="artist_name", hover_data={"artist_key":True,"exposure_score":True,"rank":True,"new_listeners":True,
        "return_rate":":.1%","repeat_listener_rate":":.1%","growth_ratio":":.2f","growth_color":False},
        color_continuous_scale=["#b64b4b", "#d4d4d4", "#3979b8"], color_continuous_midpoint=0,
        labels={"new_listeners":"New listeners","return_rate":"Return rate","growth_color":"Growth (x)","window_listeners":"Listeners"}, log_x=True)
    fig.update_layout(coloraxis_colorbar_title="Growth (log₂)")
    st.plotly_chart(fig, use_container_width=True, on_select=_selected_from_scatter, selection_mode="points", key="shortlist_scatter")
