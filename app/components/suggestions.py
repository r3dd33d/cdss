import streamlit as st

_EXAMPLES = [
    "Stage III NSCLC, EGFR exon 19 deletion, on osimertinib, no prior chemo",
    "HER2-positive breast cancer, stage II, no current treatment",
    "Metastatic colorectal cancer, KRAS G12C mutation, post-first-line",
]


def render() -> str | None:
    """Show suggestion chips; return clicked text or None."""
    st.caption("Try an example:")
    cols = st.columns(len(_EXAMPLES))
    for col, example in zip(cols, _EXAMPLES):
        if col.button(example[:40] + "…", use_container_width=True):
            return example
    return None
