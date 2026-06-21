"""Bridge between the Streamlit UI and the headless cdss core.

Starts the async pipeline on a background thread so the Streamlit script
thread stays responsive. The background thread MUST NOT call st.* — it
has no ScriptRunContext.
"""
from __future__ import annotations

import asyncio
import threading
from queue import Queue, Empty

from cdss.observability.events import AgentEvent
from cdss.core.models.report import FinalReport
from cdss.pipeline.runner import Runner


class RunHandle:
    """Exposes run events and result to the UI thread."""

    def __init__(self, run_id: str, queue: Queue) -> None:
        self.run_id = run_id
        self._queue = queue
        self._done = False
        self._result: FinalReport | None = None
        self._error: Exception | None = None

    def drain_events(self) -> list[AgentEvent]:
        events = []
        while True:
            try:
                item = self._queue.get_nowait()
                if item is None:
                    self._done = True
                    break
                if isinstance(item, Exception):
                    self._error = item
                    self._done = True
                    break
                if isinstance(item, FinalReport):
                    self._result = item
                else:
                    events.append(item)
            except Empty:
                break
        return events

    def done(self) -> bool:
        return self._done

    def result(self) -> FinalReport | None:
        return self._result

    def error(self) -> Exception | None:
        return self._error


def start_run(runner: Runner, text: str, files: list | None = None) -> RunHandle:
    """Validate input, then start the pipeline on a background thread."""
    if not text or not text.strip():
        raise ValueError("Message cannot be empty.")
    if len(text) > 8000:
        raise ValueError("Message too long (max 8000 characters).")

    is_pdf = False
    raw_input = text.strip()

    # PDF: extract text before handing to the core.
    if files:
        from cdss.sources.extract.pdf import extract_pdf
        raw_input = extract_pdf(files[0].read())
        is_pdf = True

    # Subscribe to the event bus before starting to avoid missing early events.
    q_events = runner.bus.subscribe(f"run_")  # will be overridden per run_id
    q_bridge: Queue = Queue()

    def _thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            report = loop.run_until_complete(runner.run(raw_input, is_pdf=is_pdf))
            q_bridge.put(report)
            q_bridge.put(None)  # sentinel
        except Exception as exc:
            q_bridge.put(exc)
        finally:
            loop.close()

    # Wire the runner's event bus to the bridge queue.
    run_id_holder: list[str] = []

    original_publish = runner.bus.publish

    def _intercepting_publish(event: AgentEvent) -> None:
        original_publish(event)
        if not run_id_holder:
            run_id_holder.append(event.run_id)
        q_bridge.put(event)

    runner.bus.publish = _intercepting_publish  # type: ignore[method-assign]

    t = threading.Thread(target=_thread, daemon=True)
    t.start()

    # Approximate run_id; bridge queue carries all events anyway.
    handle = RunHandle(run_id="pending", queue=q_bridge)
    return handle
