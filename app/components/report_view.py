import streamlit as st

from cdss.core.models.report import FinalReport
from cdss.llm.prompts.synthesizer import DISCLAIMER


def render(report: FinalReport) -> None:
    """Render the final report in a tabbed view inside a chat message."""
    tabs = st.tabs(["📋 Profile", "🏥 Standard Care", "🔬 Trials", "💊 Off-Label"])

    with tabs[0]:
        p = report.profile
        st.markdown(f"**Condition:** {p.condition or '—'}")
        st.markdown(f"**Stage:** {p.stage or '—'}")
        if p.biomarkers:
            for b in p.biomarkers:
                st.markdown(f"- **{b.gene}** {b.variant_type}")
        if p.current_medications:
            st.markdown("**Current medications:** " + ", ".join(p.current_medications))

    with tabs[1]:
        st.markdown(report.markdown)

    with tabs[2]:
        matched = report.trials_matched_count
        analyzed = report.trials_analyzed_count
        if matched == 0:
            st.info("No matching trials found.")
        else:
            st.markdown(
                f"**{matched} trial(s) matched** in search; "
                f"**{analyzed} analyzed** in depth (see report above)."
            )

    with tabs[3]:
        if report.hypotheses_count == 0:
            st.info("No off-label hypotheses generated.")
        else:
            st.markdown(f"{report.hypotheses_count} hypotheses included in the report above.")

    st.caption(DISCLAIMER)
