# Contract — Agent Event Stream (in-process)

Per-run stream that lets the UI build the live agent-trace tree (US2, FR-008/009).
Emitted by the `EventBus`; the sole authority for spawn/lifecycle events is
`AgentFactory.spawn()` (Constitution IV). Events are plain `AgentEvent` objects the
UI drains via `runner_bridge` (`drain_events()`) — **no SSE/HTTP wire format**.

## Event object (`AgentEvent`)

| Field | Type | Notes |
|-------|------|-------|
| run_id | str | id of the emitting unit (run or agent) |
| parent_run_id | str \| null | builds the tree |
| agent_type | str \| null | from `AgentType` |
| event_type | str | from `EventType` |
| label | str | human label, e.g. "Reading nccn.org/…" |
| timestamp | str (ISO-8601) | |
| duration_ms | int \| null | on completion events |
| payload | object | event-specific, PII-redacted |

## Event sequence (happy path)

Ordered `event_type`s the UI receives for one run:

```
run_started        run_id=run_abc123
agent_spawned      INTAKE              parent=run_abc123
agent_completed    INTAKE              2100ms
agent_spawned      RESEARCH_COORDINATOR parent=run_abc123
source_discovered  url=…nccn.org…      (×N)
agent_spawned      SOURCE_READER       parent=<coord>   (×N, parallel)
source_fetched     url=…  char_count=… duration_ms=…
agent_completed    SOURCE_READER       4200ms           (per reader)
agent_failed       SOURCE_READER       error=timeout    (isolated failure, SC-003)
agent_completed    RESEARCH_AGGREGATOR 1200ms
phase_completed    phase=research
... (trials, cross_indication, synthesize) ...
run_completed      run_id=run_abc123   total_duration_ms=…
```

## Guarantees

- Every `agent_spawned` carries a `parent_run_id` so the UI renders a tree without
  server-side tree state; `agent_trace.py` maps status to `st.status` (running →
  "running", completed → "complete", failed → "error").
- A failed source emits `agent_failed` but the run continues and still reaches
  `run_completed` (partial results) — never aborts on a single leaf failure.
- Exactly one terminal event per run: `run_completed` **or** `run_failed`; after the
  UI drains it, `RunHandle.done()` is true and no further events arrive.
- Events are append-only and ordered per run (backed by `TraceStore`); a late first
  `drain_events()` replays prior events, then live ones.
- No secrets or raw patient text in `payload` (Constitution V) — labels/previews are
  redacted/truncated.
