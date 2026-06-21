from unittest.mock import MagicMock

import pytest

from cdss.llm.model_selector import select_model


def _mock_client(model_ids: list[str]) -> MagicMock:
    client = MagicMock()
    client.models.list.return_value.data = [MagicMock(id=m) for m in model_ids]
    return client


PREFERENCE = ["deepseek-r1-distill-llama-70b", "llama-3.3-70b-versatile", "llama3-8b-8192"]


def test_picks_first_preferred():
    client = _mock_client(["llama3-8b-8192", "deepseek-r1-distill-llama-70b"])
    assert select_model(client, PREFERENCE) == "deepseek-r1-distill-llama-70b"


def test_falls_back_to_next_preferred():
    client = _mock_client(["llama3-8b-8192", "llama-3.3-70b-versatile"])
    assert select_model(client, PREFERENCE) == "llama-3.3-70b-versatile"


def test_falls_back_to_any_available():
    client = _mock_client(["some-unknown-model"])
    result = select_model(client, PREFERENCE)
    assert result == "some-unknown-model"


def test_raises_when_no_models():
    client = _mock_client([])
    with pytest.raises(RuntimeError, match="No models available"):
        select_model(client, PREFERENCE)
