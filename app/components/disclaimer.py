import streamlit as st

_TEXT = (
    ":material/warning: **Research tool only — not medical advice.** "
    "Confirm all findings with a qualified physician before making any treatment decisions."
)


def render() -> None:
    st.warning(_TEXT)
