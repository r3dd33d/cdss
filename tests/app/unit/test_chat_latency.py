import time
from unittest.mock import MagicMock, patch

from cdss.core.models.route import RouteDecision


def test_chat_path_does_not_invoke_runner():
    """SC-001: chat routing completes quickly without pipeline runner."""
    mock_decision = RouteDecision(mode="chat", confidence=0.9)
    with patch("app.chat_bridge.route_message_sync", return_value=mock_decision):
        with patch("app.chat_bridge.chat_reply_sync", return_value="HER2 is a protein."):
            with patch("cdss.pipeline.runner.Runner.run") as mock_run:
                from app.chat_bridge import route_and_reply
                start = time.monotonic()
                decision, reply = route_and_reply("What is HER2?")
                elapsed = time.monotonic() - start

    assert decision.mode == "chat"
    assert reply
    mock_run.assert_not_called()
    assert elapsed < 5.0
