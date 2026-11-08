"""Sidebar state is private to this module."""
import streamlit as st
from analysis.config import ScoringParams
from analysis.scoring import SCORE_COMPONENTS

DEFAULTS = {"controls_population": "All listeners", "controls_band": (5, 200),
            "controls_evidence": 5, "controls_single": True,
            **{f"controls_weight_{k}": v for k, v in ScoringParams().weights.items()}}


def reset():
    for key, value in DEFAULTS.items():
        st.session_state[key] = value
    st.session_state["controls_last_weights"] = dict(ScoringParams().weights)


def render():
    for key, value in DEFAULTS.items():
        st.session_state.setdefault(key, value)
    with st.sidebar:
        st.header("Exposure settings")
        choice = st.radio("Population", ["All listeners", "Exclude heavy users"], key="controls_population")
        lo, hi = st.slider("Listener band", 2, 1000, key="controls_band")
        evidence = st.slider("Retention sample minimum", 1, 30, key="controls_evidence")
        single = st.checkbox("Exclude single-fan risk", key="controls_single")
        with st.expander("Score weights"):
            labels = ["Audience reach", "Listening depth", "Audience diversity", "Repeat engagement"]
            weights = {k: st.slider(label, 0.0, 1.0, step=0.05, key=f"controls_weight_{k}")
                       for k, label in zip(SCORE_COMPONENTS, labels)}
        if sum(weights.values()) == 0:
            st.error("At least one score weight must be positive. Using the last valid weights.")
            weights = dict(st.session_state.get("controls_last_weights", ScoringParams().weights))
        else:
            st.session_state["controls_last_weights"] = dict(weights)
        st.button("Reset", on_click=reset, key="controls_reset")
    return ("all" if choice == "All listeners" else "exclude_heavy",
            ScoringParams(min_listeners=lo, max_listeners=hi, min_eligible_new=evidence,
                          exclude_single_fan=single, weights=weights))
