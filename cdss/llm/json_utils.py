import re


def strip_json_fences(text: str) -> str:
    """Remove markdown ```json ... ``` fences that models sometimes add."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()
