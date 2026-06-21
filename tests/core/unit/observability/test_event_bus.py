import threading

from cdss.core.enums import AgentType, EventType
from cdss.observability.event_bus import EventBus
from cdss.observability.events import AgentEvent
from cdss.observability.trace_store import TraceStore


def _bus() -> EventBus:
    return EventBus(TraceStore())


def _evt(run_id: str, etype: EventType = EventType.RUN_STARTED) -> AgentEvent:
    return AgentEvent.build(etype, run_id, label="test")


def test_subscribe_and_drain():
    bus = _bus()
    q = bus.subscribe("r1")
    bus.publish(_evt("r1"))
    assert q.get_nowait().run_id == "r1"


def test_close_sends_sentinel():
    bus = _bus()
    q = bus.subscribe("r1")
    bus.close("r1")
    assert q.get_nowait() is None


def test_event_ordering():
    bus = _bus()
    q = bus.subscribe("r1")
    for i in range(5):
        bus.publish(AgentEvent.build(EventType.AGENT_SPAWNED, "r1", label=str(i)))
    labels = [q.get_nowait().label for _ in range(5)]
    assert labels == [str(i) for i in range(5)]


def test_pii_redacted():
    bus = _bus()
    q = bus.subscribe("r1")
    bus.publish(AgentEvent.build(EventType.RUN_STARTED, "r1", raw_input="secret"))
    evt = q.get_nowait()
    assert "raw_input" not in evt.payload


def test_cross_thread_publish():
    bus = _bus()
    q = bus.subscribe("r1")
    results = []

    def publisher():
        for _ in range(10):
            bus.publish(_evt("r1"))

    t = threading.Thread(target=publisher)
    t.start()
    t.join()
    while not q.empty():
        results.append(q.get_nowait())
    assert len(results) == 10
