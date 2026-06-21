INTAKE_PROMPT = """\
You are a medical information extractor. Extract structured patient information \
from the text below. Return ONLY valid JSON with these exact keys:
{{
  "condition": "<primary diagnosis or empty string>",
  "stage": "<disease stage or empty string>",
  "biomarkers": [{{"gene": "", "variant_type": "", "details": ""}}],
  "current_medications": ["<medication name>"],
  "prior_therapies": ["<therapy name>"]
}}
Do NOT invent information not present in the text. Leave fields empty if unknown.

Patient text:
{patient_text}
"""
