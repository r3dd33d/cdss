TRIAL_AGGREGATOR_PROMPT = """\
Merge the following clinical trial summaries into one Markdown section for a patient report.
Condition: {condition} {stage}
Trials matched in search: {matched_count}
Trials analyzed in depth: {analyzed_count}

For each trial include NCT id, title, phase, status, eligibility highlights, and patient fit notes.
If analyzed count is less than matched count, note that only the top-ranked trials were deep-read.
If any reader failed, mention gaps briefly.

Trial summaries:
{summaries}
"""
