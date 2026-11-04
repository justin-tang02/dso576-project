import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.fmt import count, rate

DEFINITIONS = [
    ("Listen", "One cleaned row of the dump."),
    ("Window", "UTC days 2026-09-01 to 2026-09-28 inclusive; older rows count only as history."),
    ("Early / late", "Window days 1–14 / 15–28."),
    ("Artist", "Whitespace-collapsed, NFKC, casefolded credit string; collaborations are one entity."),
    ("New listener", "First observed listen of the artist falls inside the window; this is not proven discovery."),
    ("Eligible / returned", "New listener discovered by Sep 21; returned means another play 1–7 days after first day."),
    ("Segment", "Listener's total window listens: light <50, moderate 50–499, heavy 500+."),
    ("Emerging / established", "Window audience size is controlled by the listener band; above its ceiling is established."),
    ("Single-fan risk", "Top listener's share of artist listens exceeds 50%."),
    ("Exposure score", "Weighted percentile score of new listeners, return rate, repeat rate and growth within shortlist."),
]


def render(ctx):
    daily = ctx.tables["daily_coverage"].copy().sort_values("listen_day")
    daily["listen_day"] = pd.to_datetime(daily.listen_day)
    fig = go.Figure()
    outside = ~daily.in_window.astype(bool)
    fig.add_bar(x=daily.listen_day, y=daily.listens, marker_color=["#9aa0a6" if x else "#4c78a8" for x in outside], name="Listens")
    fig.update_layout(title="Daily coverage (all users)", xaxis_title="UTC day", yaxis_title="Listens", showlegend=False)
    fig.add_vrect(x0="2026-09-01", x1="2026-09-29", fillcolor="gray", opacity=.18, line_width=0, layer="below")
    st.plotly_chart(fig, use_container_width=True)
    q = ctx.manifest.get("data_quality", {})
    def day(key):
        value = q.get(key)
        return str(value)[:10] if value else "n/a"
    facts = [
        ("Listen range", f"{day('first_listen_utc')} to {day('last_listen_utc')}"),
        ("Total listens", count(q.get("total_listens"))), ("Window listens", count(q.get("window_listens"))),
        ("Window share", rate(q.get("window_share"), 1)), ("Window listeners", count(q.get("window_listeners"))),
        ("Window artists", count(q.get("window_artists"))), ("MBID share", rate(q.get("window_mbid_share"), 1)),
        ("Window listens from flagged heavy users", rate(q.get("window_heavy_user_listen_share"), 1)),
        ("Flagged heavy users in window", count(q.get("window_heavy_users"))),
        ("Multi-day listener share", rate(q.get("multi_day_listener_share"), 1)),
        ("Sufficiency", f"{'Pass' if q.get('retention_sufficient') else 'Fail'} (threshold 20%)"),
        ("Last eligible discovery day", day("last_eligible_discovery")),
        ("Artist listeners p50 / p90 / p99 / max", " / ".join(count(q.get(k)) for k in ["artist_listeners_p50","artist_listeners_p90","artist_listeners_p99","artist_listeners_max"])),
    ]
    st.markdown("**Data quality facts**")
    st.caption("Over stored artists (2+ listeners), all users.")
    st.dataframe(pd.DataFrame(facts, columns=["Fact","Value"]), hide_index=True, use_container_width=True)
    st.markdown("**Definitions**")
    st.dataframe(pd.DataFrame(DEFINITIONS, columns=["Term","Definition"]), hide_index=True, use_container_width=True)
    st.markdown("**Limits**")
    st.write("ListenBrainz users are not a random sample of streaming listeners; first observed listen is not true discovery; name keys can merge namesakes; associations only, not the effect of exposure.")
