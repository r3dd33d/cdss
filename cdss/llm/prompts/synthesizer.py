DISCLAIMER = (
    "**This tool is for research and education only. It is not medical advice.** "
    "Clinical trial eligibility must be confirmed by a qualified physician. "
    "Off-label therapy hypotheses require evaluation by your specialist. "
    "Never start, stop, or change treatment based on this report alone."
)

SYNTHESIZER_PROMPT = """\
You are a medical research assistant. Compile the information below into a clear, \
plain-English patient research report in Markdown.

Include these sections in order:
1. ## Patient Profile
2. ## Standard of Care
3. ## Clinical Trials ({trials_count} found)
4. ## Off-Label Hypotheses ({hypotheses_count} found)
5. ## Important Disclaimer

For section 5 use EXACTLY this text:
{disclaimer}

Patient Profile: {profile}
Standard Care Summary: {standard_care}
Clinical Trials: {trials}
Off-Label Hypotheses: {hypotheses}
Validation Flags: {flags}
"""
