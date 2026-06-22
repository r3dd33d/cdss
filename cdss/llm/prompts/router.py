ROUTER_PROMPT = """\
Classify the user message for a clinical research assistant app.
Return ONLY valid JSON:
{{
  "mode": "chat" | "research" | "clarify",
  "confidence": 0.0,
  "clarifying_question": ""
}}

Rules:
- "research" if the user describes a patient case, diagnosis, stage, biomarkers, or asks for trials/treatment research.
- "chat" if the user asks a general educational oncology question without a personal case.
- "clarify" only if genuinely ambiguous; set clarifying_question to one short question.

User message:
{text}
Has prior report in session: {has_prior_report}
"""
