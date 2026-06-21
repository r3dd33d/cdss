"""T070: empty / over-length input raises ValueError before starting a run."""
import pytest
from unittest.mock import MagicMock, patch


def _bridge_start(runner, text, files=None):
    from app.runner_bridge import start_run
    return start_run(runner, text, files)


def test_empty_text_raises():
    runner = MagicMock()
    with pytest.raises(ValueError, match="empty"):
        _bridge_start(runner, "")


def test_whitespace_only_raises():
    runner = MagicMock()
    with pytest.raises(ValueError, match="empty"):
        _bridge_start(runner, "   ")


def test_over_length_raises():
    runner = MagicMock()
    with pytest.raises(ValueError, match="long"):
        _bridge_start(runner, "x" * 8001)


def test_valid_text_does_not_raise():
    runner = MagicMock()
    runner.bus.publish = MagicMock()
    runner.bus.subscribe = MagicMock(return_value=MagicMock())
    with patch("threading.Thread") as mock_thread:
        mock_thread.return_value.start = MagicMock()
        handle = _bridge_start(runner, "Stage III NSCLC, EGFR exon 19 deletion.")
    assert handle is not None
