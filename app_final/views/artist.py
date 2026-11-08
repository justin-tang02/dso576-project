"""V3 artist detail and score breakdown."""

import pandas as pd
import plotly.express as px
import streamlit as st


def render(ctx):
    df = ctx.scored.sort_values(
        "v3_score", ascending=False
    ).reset_index(drop=True).copy()

    df["rank"] = df.index + 1

    st.subheader("Artist Detail")

    labels = {
        row.artist_key: f"#{row.rank} · {row.artist_name}"
        for row in df.itertuples()
    }

    keys = df.artist_key.tolist()
    requested = st.session_state.get("selected_artist")
    current = requested if requested in labels else keys[0]

    if st.session_state.get("v3_artist_picker") != current:
        st.session_state["v3_artist_picker"] = current

    selected = st.selectbox(
        "Select an artist",
        options=keys,
        format_func=lambda key: labels.get(key, key),
        key="v3_artist_picker",
        on_change=lambda: st.session_state.update(
            selected_artist=st.session_state["v3_artist_picker"]
        ),
    )

    row = df.set_index("artist_key").loc[selected]

    st.subheader(row.artist_name)
    st.caption(
        f"Rank #{int(row['rank']):,} of {len(df):,} "
        f"· V3 score: {row.v3_score:.1f}/100"
    )

    a, b, c, d = st.columns(4)
    a.metric("September listeners", f"{row.sep_listeners:,}")
    b.metric(
        "October listeners",
        f"{row.oct_listeners:,}",
        delta=f"{row.audience_change:+,}",
    )
    c.metric("Audience growth", f"{row.audience_growth_pct:+.1f}%")
    d.metric("Recurring listener rate", f"{row.retention_rate:.1%}")

    st.subheader("Audience Comparison")

    comparison = pd.DataFrame({
        "Snapshot": ["September 28", "October 27"],
        "Listeners": [row.sep_listeners, row.oct_listeners],
        "Listens": [row.sep_listens, row.oct_listens],
    })

    fig = px.bar(
        comparison,
        x="Snapshot",
        y="Listeners",
        text="Listeners",
        labels={"Listeners": "Unique listeners"},
    )
    st.plotly_chart(fig, width="stretch")

    st.subheader("Listening Behavior")

    a, b, c, d = st.columns(4)
    a.metric("Recurring listeners", f"{row.recurring_listeners:,}")
    b.metric("September depth", f"{row.sep_depth:.2f}")
    c.metric("October depth", f"{row.oct_depth:.2f}")
    d.metric(
        "Top-listener share",
        f"{row.oct_top_listener_share:.1%}",
    )

    st.caption(
        "Depth = listens per observed listener. "
        "Top-listener share = proportion of October listens "
        "attributed to the artist's most active listener."
    )

    st.subheader("V3 Score Breakdown")

    components = pd.DataFrame({
        "Component": ["Growth", "Retention", "Depth", "Breadth"],
        "Percentile score": [
            row.growth_score,
            row.retention_score,
            row.depth_score,
            row.breadth_score,
        ],
        "Weight": [0.35, 0.30, 0.20, 0.15],
    })

    components["Weighted contribution"] = (
        components["Percentile score"] * components["Weight"]
    )

    fig = px.bar(
        components,
        x="Component",
        y="Weighted contribution",
        text="Weighted contribution",
        labels={
            "Weighted contribution": "Points toward V3 score",
        },
    )
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    st.plotly_chart(fig, width="stretch")

    st.dataframe(
        components.round(2),
        hide_index=True,
        width="stretch",
    )

    st.caption(
        "Weights: growth 35%, retention 30%, depth 20%, "
        "breadth 15%. Higher breadth scores indicate less "
        "concentration in a single listener."
    )

    st.info(
        "These snapshots measure observed activity among matched "
        "ListenBrainz users. They do not establish when an artist "
        "actually emerged or whether promotional exposure caused growth."
    )

    st.divider()
    st.subheader("Compare Artists")
    st.caption(
        "Compare the selected artist with up to three others. "
        "All scores and original ranks are preserved."
    )

    other_keys = [key for key in keys if key != selected]

    compare_keys = st.multiselect(
        "Choose up to three additional artists",
        options=other_keys,
        format_func=lambda key: labels.get(key, key),
        max_selections=3,
        key="v3_artist_compare",
    )

    if compare_keys:
        compared = df.set_index("artist_key").loc[
            [selected, *compare_keys]
        ].reset_index()

        st.subheader("Performance Comparison")

        comparison = pd.DataFrame({
            "Artist": compared.artist_name,
            "Rank": compared["rank"],
            "V3 Score": compared.v3_score.round(1),
            "Sep Listeners": compared.sep_listeners,
            "Oct Listeners": compared.oct_listeners,
            "Audience Change": compared.audience_change,
            "Growth (%)": compared.audience_growth_pct.round(1),
            "Retention (%)": (compared.retention_rate * 100).round(1),
            "Oct Depth": compared.oct_depth.round(2),
            "Top Listener (%)": (
                compared.oct_top_listener_share * 100
            ).round(1),
        })

        st.dataframe(
            comparison,
            hide_index=True,
            width="stretch",
        )

        fig = px.bar(
            compared,
            x="artist_name",
            y="v3_score",
            color="artist_name",
            text="v3_score",
            labels={
                "artist_name": "Artist",
                "v3_score": "V3 score",
            },
        )
        fig.update_traces(
            texttemplate="%{text:.1f}",
            textposition="outside",
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width="stretch")

        st.subheader("Scoring Component Comparison")

        weights = {
            "Growth": ("growth_score", 0.35),
            "Retention": ("retention_score", 0.30),
            "Depth": ("depth_score", 0.20),
            "Breadth": ("breadth_score", 0.15),
        }

        component_rows = []

        for row in compared.itertuples():
            for component, (column, weight) in weights.items():
                component_rows.append({
                    "Artist": row.artist_name,
                    "Component": component,
                    "Weighted Points": getattr(row, column) * weight,
                })

        components = pd.DataFrame(component_rows)

        fig = px.bar(
            components,
            x="Component",
            y="Weighted Points",
            color="Artist",
            barmode="group",
            labels={
                "Weighted Points": "Points toward V3 score",
            },
        )

        st.plotly_chart(fig, width="stretch")

        st.caption(
            "Growth contributes 35%, retention 30%, depth 20%, "
            "and breadth 15%. Component values are weighted "
            "percentile scores, not raw metric values."
        )

    else:
        st.info(
            "Select another artist above to compare audience "
            "performance and scoring components."
        )

    st.divider()
    st.subheader("Entry Track Insights")

    st.caption("First tracks played by new listeners and their 7-day return rates. Based on September 1–28, 2026 listening data.")

    tracks = ctx.entry_tracks.loc[
        ctx.entry_tracks.artist_key.eq(selected)
    ].copy()

    tracks = tracks.sort_values(
        ["new_listeners", "entry_track_name"],
        ascending=[False, True],
    ).head(10)

    if tracks.empty:
        st.info("No entry-track evidence is available for this artist.")
    else:
        minimum_evidence = 5

        def format_return(row):
            eligible = row.eligible_new_listeners
            if eligible < minimum_evidence:
                return f"Too few (n={eligible:,})"
            if pd.isna(row.return_rate):
                return "N/A"
            return f"{row.return_rate:.1%}"

        display = pd.DataFrame({
            "Track": tracks.entry_track_name,
            "New Listeners": tracks.new_listeners,
            "Eligible": tracks.eligible_new_listeners,
            "Returned": tracks.returned_new_listeners,
            "7-Day Return Rate": [
                format_return(r) for r in tracks.itertuples()
            ],
        })

        st.dataframe(
            display,
            hide_index=True,
            width="stretch",
        )

        st.caption(
            "Entry track means the first observed track played by "
            "a new listener. Return rates are displayed only when "
            "at least 5 listeners have a complete 7-day observation "
            "window. These September metrics are separate from "
            "the two-snapshot audience momentum scores."
        )
