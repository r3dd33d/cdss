import streamlit as st

_EXAMPLES: list[tuple[str, str]] = [
    (
        "NSCLC · EGFR",
        "Stage III NSCLC, EGFR exon 19 deletion, on osimertinib, no prior chemo",
    ),
    (
        "HER2+ breast",
        "HER2-positive breast cancer, stage II, no current treatment",
    ),
    (
        "CRC · KRAS",
        "Metastatic colorectal cancer, KRAS G12C mutation, post-first-line",
    ),
]

_LABELS = [label for label, _ in _EXAMPLES]
_LOOKUP = dict(_EXAMPLES)


def render() -> str | None:
    """Show uniform suggestion pills; return full example text or None."""
    st.caption("Try an example:")
    selected = st.pills(
        "examples",
        _LABELS,
        selection_mode="single",
        label_visibility="collapsed",
    )
    if selected:
        return _LOOKUP[selected]
    return None
