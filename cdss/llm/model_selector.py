from openai import OpenAI


def select_model(client: OpenAI, preference_order: list[str]) -> str:
    """Pick the first available model from the preference list; fall back to any available."""
    available = {m.id for m in client.models.list().data}
    for model in preference_order:
        if model in available:
            return model
    if available:
        return sorted(available)[0]
    raise RuntimeError("No models available from Groq.")
