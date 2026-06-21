from openai import OpenAI

from cdss.llm.model_selector import select_model


class LLMClient:
    """Thin wrapper around the Groq OpenAI-compatible endpoint."""

    def __init__(self, api_key: str, preference_order: list[str]) -> None:
        self._client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key,
        )
        self._model = select_model(self._client, preference_order)

    @property
    def model(self) -> str:
        return self._model

    def chat(self, prompt: str, max_tokens: int = 1024) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()
