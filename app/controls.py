from analysis.config import ScoringParams
import streamlit as st

DEFAULTS = {"population": "all", "band": (5, 200), "evidence": 5, "exclude": True,
            "w_new": .25, "w_return": .25, "w_repeat": .25, "w_growth": .25}


def sidebar_controls():
    if st.sidebar.button("Reset", use_container_width=True):
        for key, value in DEFAULTS.items():
            st.session_state[key] = value
    population_label = st.sidebar.radio("Population", ["All listeners", "Exclude heavy users"], key="population",
                                        format_func=lambda x: x)
    population = "all" if population_label == "All listeners" else "exclude_heavy"
    low, high = st.sidebar.slider("Listener band", 2, 1000, (5, 200), key="band")
    evidence = st.sidebar.slider("Evidence minimum", 1, 30, 5, key="evidence")
    exclude = st.sidebar.checkbox("Exclude single-fan risk", True, key="exclude")
    with st.sidebar.expander("Score weights"):
        weights = {
            "new_listeners": st.slider("New listeners", 0.0, 1.0, .25, .05, key="w_new"),
            "return_rate": st.slider("Return rate", 0.0, 1.0, .25, .05, key="w_return"),
            "repeat_listener_rate": st.slider("Repeat rate", 0.0, 1.0, .25, .05, key="w_repeat"),
            "growth_ratio": st.slider("Growth", 0.0, 1.0, .25, .05, key="w_growth"),
        }
    total = sum(weights.values())
    if total == 0:
        st.sidebar.error("At least one score weight must be above 0. Using the last valid weights.")
        weights = st.session_state.get("_last_valid_weights", dict.fromkeys(weights, .25))
    else:
        st.session_state["_last_valid_weights"] = weights.copy()
    return population, ScoringParams(min_listeners=low, max_listeners=high,
        min_eligible_new=evidence, exclude_single_fan=exclude, weights=weights)
