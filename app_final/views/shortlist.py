"""V3 artist shortlist and ranking exploration."""

import pandas as pd
import plotly.express as px
import streamlit as st


def select_table():
    selection = st.session_state["v3_shortlist_table"]["selection"]["rows"]
    if selection:
        keys = st.session_state["v3_visible_artist_keys"]
        st.session_state["selected_artist"] = keys[selection[0]]


def select_scatter():
    points = st.session_state["v3_shortlist_scatter"]["selection"]["points"]
    if points:
        st.session_state["selected_artist"] = points[0]["customdata"][0]


def render(ctx):
    df = ctx.scored.sort_values(
        "v3_score", ascending=False
    ).reset_index(drop=True).copy()

    df["rank"] = df.index + 1

    st.subheader("Emerging Artist Shortlist")
    st.caption(
        "Artists ranked by observed audience momentum among "
        "matched listeners across two snapshots."
    )

    a, b, c, d = st.columns(4)
    a.metric("Ranked artists", f"{len(df):,}")
    b.metric("Median September audience", f"{df.sep_listeners.median():,.0f}")
    c.metric("Median October audience", f"{df.oct_listeners.median():,.0f}")
    d.metric("Artists with audience growth", f"{(df.audience_change > 0).sum():,}")

    st.divider()

    st.subheader("Discover Artists")

    a, b, c, d = st.columns(4)

    with a:
        min_growth = st.slider(
            "Minimum growth (%)",
            min_value=-100,
            max_value=500,
            value=-100,
            step=10,
        )

    with b:
        min_retention = st.slider(
            "Minimum retention (%)",
            min_value=0,
            max_value=100,
            value=0,
            step=5,
        )

    with c:
        max_audience = st.slider(
            "Maximum October listeners",
            min_value=5,
            max_value=200,
            value=200,
            step=5,
        )

    with d:
        max_concentration = st.slider(
            "Maximum top-listener share (%)",
            min_value=0,
            max_value=100,
            value=100,
            step=5,
        )

    search = st.text_input(
        "Search artists",
        placeholder="Enter an artist name",
    )

    shown = df.loc[
        (df.audience_growth_pct >= min_growth)
        & (df.retention_rate >= min_retention / 100)
        & (df.oct_listeners <= max_audience)
        & (df.oct_top_listener_share <= max_concentration / 100)
        & df.artist_name.str.contains(
            search, case=False, regex=False, na=False
        )
    ].copy()

    st.caption(
        f"Showing {len(shown):,} of {len(df):,} ranked artists. "
        "Original V3 ranks and scores are preserved."
    )

    if shown.empty:
        st.info("No artists match your search.")
        return

    st.subheader("Growth vs. Retention")

    shown["audience_growth_fraction"] = shown["audience_growth_pct"] / 100

    fig = px.scatter(
        shown,
        x="audience_growth_fraction",
        y="retention_rate",
        size="oct_listeners",
        color="v3_score",
        hover_name="artist_name",
        custom_data=[
            "artist_key", "rank", "sep_listeners", "oct_listeners",
            "audience_change", "v3_score",
        ],
        color_continuous_scale="Blues",
        labels={
            "audience_growth_fraction": "Audience growth",
            "retention_rate": "Recurring listener rate",
            "v3_score": "V3 score",
        },
    )

    fig.update_xaxes(tickformat=".0%")
    fig.update_yaxes(tickformat=".0%")
    fig.update_layout(height=480)

    st.plotly_chart(
        fig,
        width="stretch",
        key="v3_shortlist_scatter",
        on_select=select_scatter,
        selection_mode="points",
    )

    st.subheader("Ranked Artists")

    display = pd.DataFrame({
        "Rank": shown["rank"],
        "Artist": shown["artist_name"],
        "Score": shown["v3_score"].round(1),
        "Sep listeners": shown["sep_listeners"],
        "Oct listeners": shown["oct_listeners"],
        "Change": shown["audience_change"],
        "Growth": shown["audience_growth_pct"].map(lambda x: f"{x:+.1f}%"),
        "Retention": shown["retention_rate"].map(lambda x: f"{x:.1%}"),
        "Oct depth": shown["oct_depth"].round(2),
        "Top-listener share": shown["oct_top_listener_share"].map(
            lambda x: f"{x:.1%}"
        ),
    })

    st.session_state["v3_visible_artist_keys"] = shown.artist_key.tolist()

    st.dataframe(
        display,
        hide_index=True,
        width="stretch",
        key="v3_shortlist_table",
        on_select=select_table,
        selection_mode="single-row",
    )

    selected = st.session_state.get("selected_artist")
    match = df.loc[df.artist_key.eq(selected)]
    if not match.empty:
        st.success(
            f"Selected: {match.iloc[0].artist_name}. "
            "Open the Artist Detail tab to investigate."
        )

    st.download_button(
        "Download full V3 rankings",
        df.to_csv(index=False).encode("utf-8"),
        file_name="v3_artist_rankings.csv",
        mime="text/csv",
    )

    st.caption(
        "Scores are relative to eligible artists in this dataset. "
        "Growth reflects observed listener counts in the two snapshots, "
        "not a complete month-over-month audience estimate."
    )
