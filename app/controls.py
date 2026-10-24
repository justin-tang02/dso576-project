import streamlit as st
from analysis.config import ScoringParams
from analysis.scoring import SCORE_COMPONENTS

DEFAULTS = {'controls_population': 'All listeners', 'controls_band': (5, 200),
            'controls_evidence': 5, 'controls_fan': True,
            **{f'controls_{c}': 0.25 for c in SCORE_COMPONENTS}}


def reset():
    for key, value in DEFAULTS.items():
        st.session_state[key] = value
    st.session_state['controls_valid_weights'] = ScoringParams().weights


def render():
    for key, value in DEFAULTS.items():
        st.session_state.setdefault(key, value)
    with st.sidebar:
        st.header('Shape the shortlist')
        population = st.radio('Population', ['All listeners', 'Exclude heavy users'], key='controls_population')
        lo, hi = st.slider('Listener band', 2, 1000, key='controls_band')
        evidence = st.slider('Evidence minimum', 1, 30, key='controls_evidence')
        exclude = st.checkbox('Exclude single-fan risk', key='controls_fan')
        with st.expander('Score weights'):
            labels = ['New listeners', 'Return rate', 'Repeat rate', 'Growth']
            weights = {c: st.slider(label, 0.0, 1.0, step=0.05, key=f'controls_{c}')
                       for c, label in zip(SCORE_COMPONENTS, labels)}
            if not sum(weights.values()):
                st.error('At least one weight must be positive. Using the last valid weights.')
                weights = st.session_state.get('controls_valid_weights', ScoringParams().weights)
            else:
                st.session_state['controls_valid_weights'] = weights
        st.button('Reset', on_click=reset)
    return ('all' if population == 'All listeners' else 'exclude_heavy',
            ScoringParams(min_listeners=lo, max_listeners=hi, min_eligible_new=evidence,
                          exclude_single_fan=exclude, weights=weights))
