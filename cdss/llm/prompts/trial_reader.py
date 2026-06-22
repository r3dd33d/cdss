TRIAL_READER_PROMPT = """\
Summarize this clinical trial for the patient below. Focus on eligibility criteria, \
interventions, and whether the patient may be a fit. Do NOT recommend enrollment.

Patient condition: {condition} {stage}
Biomarkers: {biomarkers}
Prior therapies: {prior_therapies}

Trial record:
{study_text}
"""
