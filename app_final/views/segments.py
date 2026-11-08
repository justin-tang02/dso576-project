"""V3 audience patterns across scored artists."""

import pandas as pd
import plotly.express as px
import streamlit as st


def render(ctx):
    df = ctx.scored.sort_values(
        "v3_score", ascending=False
    ).reset_index(drop=True).copy()

    df["rank"] = df.index + 1
    df["audience_growth_fraction"] = df["audience_growth_pct"] / 100
    df["Group"] = "Other eligible artists"
    df.loc[df["rank"] <= 100, "Group"] = "Top 100"

    st.subheader("Listener Segment Targeting")
    st.caption("Compare 7-day return rates across listener activity segments. Based on September 1–28, 2026 listening data.")

    shortlist_size = st.slider(
        "Number of top-ranked artists to evaluate",
        min_value=10,
        max_value=100,
        value=20,
        step=5,
        key="segment_shortlist_size",
    )

    shortlist_keys = set(df.head(shortlist_size)["artist_key"])

    segments = ctx.artist_segments.copy()
    segments["Group"] = "All Artists (Baseline)"
    shortlist_segments = segments.loc[
        segments["artist_key"].isin(shortlist_keys)
    ].copy()
    shortlist_segments["Group"] = "Top-ranked Artists"

    combined = pd.concat(
        [shortlist_segments, segments],
        ignore_index=True,
    )

    summary = combined.groupby(
        ["Group", "segment"], as_index=False
    ).agg(
        artists=("artist_key", "nunique"),
        listener_artist_pairs=("window_listeners", "sum"),
        new_listeners=("new_listeners", "sum"),
        eligible=("eligible_new_listeners", "sum"),
        returned=("returned_new_listeners", "sum"),
    )

    summary["return_rate"] = (
        summary["returned"] / summary["eligible"].replace(0, float("nan"))
    )

    summary["Return rate"] = summary.apply(
        lambda r: (
            f"{r['return_rate']:.1%} (n={int(r['eligible']):,})"
            if r["eligible"] >= 5
            else f"Too few (n={int(r['eligible']):,})"
        ),
        axis=1,
    )

    chart_data = summary.loc[summary["eligible"] >= 5].copy()

    if not chart_data.empty:
        fig = px.bar(
            chart_data,
            x="segment",
            y="return_rate",
            color="Group",
            barmode="group",
            text="eligible",
            category_orders={
                "segment": ["light", "moderate", "heavy"]
            },
            labels={
                "segment": "Listener activity segment",
                "return_rate": "7-day return rate",
                "eligible": "Eligible listeners",
            },
        )
        fig.update_yaxes(tickformat=".0%")
        fig.update_traces(texttemplate="n=%{text}", textposition="outside")
        st.plotly_chart(fig, width="stretch")

    st.subheader("Segment Return Rates")
    st.dataframe(
        summary[
            ["Group", "segment", "artists",
             "listener_artist_pairs", "new_listeners",
             "eligible", "returned", "Return rate"]
        ],
        hide_index=True,
        width="stretch",
    )

    st.subheader("Overall Listener Activity")

    users = ctx.segment_users.copy()
    st.dataframe(users, hide_index=True, width="stretch")

    st.caption(
        "Light: fewer than 50 listens; moderate: 50–499; "
        "heavy: 500 or more listens in the September window. "
        "Return rates describe observed listener behavior, not "
        "the causal effect of promotional exposure. "
        "Listener-artist pairs may count the same person for "
        "multiple artists."
    )

    st.divider()

    st.subheader("Audience Patterns")
    st.caption(
        "Explore how observed growth, retention, listening depth, "
        "and audience concentration vary across eligible artists."
    )

    top = df.head(100)

    a, b, c, d = st.columns(4)
    a.metric("Eligible artists", f"{len(df):,}")
    b.metric(
        "Top 100 median Sep audience",
        f"{top.sep_listeners.median():,.0f}",
    )
    c.metric(
        "Top 100 median retention",
        f"{top.retention_rate.median():.1%}",
    )
    d.metric(
        "Top 100 median concentration",
        f"{top.oct_top_listener_share.median():.1%}",
    )

    st.divider()

    st.subheader("Growth and Retention")

    fig = px.scatter(
        df,
        x="audience_growth_fraction",
        y="retention_rate",
        color="Group",
        hover_name="artist_name",
        hover_data=["sep_listeners", "oct_listeners", "v3_score"],
        opacity=0.55,
        labels={
            "audience_growth_fraction": "Observed audience growth",
            "retention_rate": "Recurring listener rate",
        },
    )
    fig.update_xaxes(tickformat=".0%", range=[-1, 4])
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Growth axis is limited to -100% through +400% for readability. "
        "Artists outside that range remain in the dataset."
    )

    st.subheader("Listening Depth Distribution")

    fig = px.histogram(
        df,
        x="oct_depth",
        color="Group",
        nbins=50,
        barmode="overlay",
        histnorm="probability density",
        labels={"oct_depth": "October listens per listener"},
    )
    st.plotly_chart(fig, width="stretch")

    st.subheader("Audience Concentration")

    fig = px.box(
        df,
        x="Group",
        y="oct_top_listener_share",
        color="Group",
        points=False,
        labels={
            "oct_top_listener_share": "Share of listens from top listener",
        },
    )
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, width="stretch")

    st.subheader("Top 100 vs. Other Eligible Artists")

    comparison = df.groupby("Group").agg(
        artists=("artist_key", "count"),
        median_sep_listeners=("sep_listeners", "median"),
        median_oct_listeners=("oct_listeners", "median"),
        median_retention=("retention_rate", "median"),
        median_depth=("oct_depth", "median"),
        median_concentration=("oct_top_listener_share", "median"),
    ).reset_index()

    st.dataframe(
        comparison.round(3),
        hide_index=True,
        width="stretch",
    )

    st.caption(
        "These comparisons are descriptive. Top-ranked artists were "
        "selected using growth, retention, depth, and breadth, so "
        "differences in those same metrics are expected."
    )
