"""Dashboard methodology, definitions, and limitations."""

import pandas as pd
import streamlit as st


def render(ctx):
    st.subheader("Data Notes & Methodology")

    st.markdown("""
### 1. Data Sources

The analysis uses two ListenBrainz listening-data snapshots:

- **September 28, 2026 (UTC)**
- **October 27, 2026 (UTC)**

Only users observed in both snapshots are included in the
matched-listener panel.

These are ingestion snapshots, not complete monthly listening
histories. A listener's absence from an artist's activity in one
snapshot does not establish that they stopped listening.

### 2. Artist Eligibility

Artists must have:

- At least 5 observed September listeners.
- At least 5 observed October listeners.
- No more than 200 observed October listeners.

These thresholds reduce instability from very small audiences
and focus the ranking on relatively smaller artists within
the observed dataset.

### 3. Scoring Method

The Exposure Score combines four components:
""")

    weights = pd.DataFrame({
        "Component": ["Growth", "Retention", "Depth", "Breadth"],
        "Weight": ["35%", "30%", "20%", "15%"],
        "Definition": [
            "Average percentile rank of percentage audience growth "
            "and absolute audience change.",
            "Percentile rank of Bayesian-smoothed recurring-listener rate.",
            "Percentile rank of October listens per listener, "
            "capped at the 95th percentile.",
            "Inverse percentile rank of the October top-listener share.",
        ],
    })

    st.dataframe(weights, hide_index=True, width="stretch")

    st.markdown("""
### 4. Metric Definitions

**Audience growth:** Percentage change in observed unique
listeners between the two snapshots.

**Recurring listeners:** Users who listened to the same artist
in both snapshots.

**Retention rate:** Recurring listeners divided by September
listeners. This is cross-snapshot recurrence, not a measured
monthly retention rate.

**Listening depth:** Number of observed listens divided by
the number of observed unique listeners.

**Top-listener share:** Proportion of an artist's October
listens contributed by their most active observed listener.
Lower concentration indicates broader distribution of activity.

### 5. Entry Tracks and Listener Segments

The dashboard also includes supporting analysis from the
**September 1–28, 2026 listening window**.

**Entry tracks:** The first observed track played by each
new listener of an artist.

**Eligible new listeners:** Listeners whose first observed
artist listen occurred early enough to allow seven full
days of follow-up within the September window.

**Seven-day return rate:** The proportion of eligible new
listeners who played the artist again within 1–7 days.

**Listener activity segments:**

- Light: fewer than 50 listens.
- Moderate: 50–499 listens.
- Heavy: 500 or more listens.

Entry-track and segment return rates are displayed only
when at least five eligible observations are available.
Small samples should still be interpreted cautiously.

These September-window measures are separate from the
two-snapshot audience rankings. They provide additional
context for editorial decisions rather than directly
contributing to the Exposure Score.

### 6. Important Limitations

- ListenBrainz users are not representative of all music listeners.
- The two snapshots do not provide continuous listening histories.
- Observed audience growth does not prove real-world artist growth.
- Artist identity is based on normalized display names, so
  collaborations, aliases, and similarly named artists can
  affect attribution.
- Retention measures recurring activity across snapshots, not
  uninterrupted engagement between them.
- The score is relative to the eligible artist population and
  is not an absolute measure of commercial potential.
- The dataset does not measure promotional exposure, so the
  analysis cannot establish causal effects of marketing.

### 7. Interpretation

This dashboard is designed to identify artists showing promising
**observed audience momentum** within the matched-listener
sample. The shortlist should be treated as a starting point
for further investigation rather than a definitive ranking
of emerging musicians.
""")

    st.subheader("Dataset Summary")

    a, b, c = st.columns(3)
    a.metric("Matched listeners", "17,827")
    b.metric("Artists in period dataset", f"{len(ctx.metrics):,}")
    c.metric("Scored artists", f"{len(ctx.scored):,}")

    st.divider()
    st.subheader("September Data Quality")

    import json
    from pathlib import Path

    manifest_path = (
        Path(__file__).resolve().parents[2]
        / "data/aggregates/manifest.json"
    )

    with open(manifest_path) as f:
        manifest = json.load(f)

    quality = manifest["data_quality"]

    a, b, c, d = st.columns(4)
    a.metric("Cleaned listens", f"{quality['total_listens']:,}")
    b.metric("September listens", f"{quality['window_listens']:,}")
    c.metric("September listeners", f"{quality['window_listeners']:,}")
    d.metric("September artists", f"{quality['window_artists']:,}")

    facts = pd.DataFrame({
        "Quality indicator": [
            "September share of cleaned listens",
            "Artist MBID coverage",
            "Flagged heavy-user listen share",
            "Flagged heavy users",
            "Multi-day listener share",
            "Retention sufficiency threshold",
            "Last eligible discovery date",
        ],
        "Value": [
            f"{quality['window_share']:.1%}",
            f"{quality['window_mbid_share']:.1%}",
            f"{quality['window_heavy_user_listen_share']:.1%}",
            f"{quality['window_heavy_users']:,}",
            f"{quality['multi_day_listener_share']:.1%}",
            "20%",
            quality["last_eligible_discovery"],
        ],
    })

    st.dataframe(facts, hide_index=True, width="stretch")

    if quality["retention_sufficient"]:
        st.success(
            "September data sufficiency check passed. "
            "At least 20% of listeners were active on multiple days."
        )
    else:
        st.warning(
            "September data sufficiency check failed. "
            "Seven-day return and repeat metrics require caution."
        )

    st.caption(
        "Quality indicators describe the September 1–28 analysis "
        "window and do not independently validate the October snapshot. "
        "MBID coverage refers to the share of listens with an artist "
        "MusicBrainz identifier."
    )
