from collections import defaultdict
from queue import Queue
from threading import Lock

from cdss.observability.events import AgentEvent
from cdss.observability.trace_store import TraceStore


class EventBus:
    """Per-run pub/sub with a thread-safe drain queue for the UI bridge."""

    def __init__(self, trace_store: TraceStore) -> None:
        self._store = trace_store
        self._lock = Lock()
        # Each run_id maps to a list of subscriber queues.
        self._queues: dict[str, list[Queue[AgentEvent | None]]] = defaultdict(list)

    def subscribe(self, run_id: str) -> Queue[AgentEvent | None]:
        """Return a queue that receives all future events for run_id."""
        q: Queue[AgentEvent | None] = Queue()
        with self._lock:
            self._queues[run_id].append(q)
        return q

    def publish(self, event: AgentEvent) -> None:
        self._store.append(event)
        with self._lock:
            for q in self._queues.get(event.run_id, []):
                q.put(event)

    def close(self, run_id: str) -> None:
        """Signal all subscribers that the run is finished."""
        with self._lock:
            for q in self._queues.pop(run_id, []):
                q.put(None)  # sentinel
