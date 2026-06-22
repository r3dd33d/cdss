import streamlit as st


def init() -> None:
    """Initialise all session-state keys if absent."""
    defaults = {
        "messages": [],
        "run_handle": None,
        "run_status": "idle",   # idle | running | completed | failed
        "events": [],
        "report": None,
        "last_report": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def reset() -> None:
    """Clear run state for a new case."""
    st.session_state.messages = []
    st.session_state.run_handle = None
    st.session_state.run_status = "idle"
    st.session_state.events = []
    st.session_state.report = None
    st.session_state.last_report = None
