from collections import defaultdict
from threading import Lock

from cdss.observability.events import AgentEvent


class TraceStore:
    """Append-only per-run event log; thread-safe."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._store: dict[str, list[AgentEvent]] = defaultdict(list)

    def append(self, event: AgentEvent) -> None:
        with self._lock:
            self._store[event.run_id].append(event)

    def get(self, run_id: str) -> list[AgentEvent]:
        with self._lock:
            return list(self._store.get(run_id, []))

    def clear(self, run_id: str) -> None:
        with self._lock:
            self._store.pop(run_id, None)
