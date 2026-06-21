class CDSSError(Exception):
    """Base for all CDSS errors."""


class FetchError(CDSSError):
    """HTTP fetch failed or timed out."""


class ExtractError(CDSSError):
    """Content extraction (HTML/PDF) failed."""


class LLMError(CDSSError):
    """LLM call failed or returned unparseable output."""


class IntakeError(CDSSError):
    """Patient input could not be parsed into a profile."""
