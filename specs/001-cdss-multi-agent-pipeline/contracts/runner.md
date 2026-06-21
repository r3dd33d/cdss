# Contract — Runner Bridge (UI → Core)

The single interface between the Streamlit `app/` and the headless `cdss/` core
(Constitution II). The UI never imports agents/LLM/pipeline directly — it calls
`app/runner_bridge.py`, which drives `cdss/pipeline/runner.py` on a background
thread and exposes events + result. No HTTP, no server, no SSE.

## Core entry (`cdss/pipeline/runner.py`)

```python
def build_runner(settings: Settings) -> Runner: ...

class Runner:
    async def run(self, raw_input: str, *, is_pdf: bool = False,
                  options: RunOptions | None = None) -> FinalReport: ...
```

- `run()` drives the LangGraph pipeline, spawning agents via `AgentFactory`, and
  publishes events to the per-run `EventBus`. Returns the `FinalReport`.
- The core is UI-agnostic: it imports no `streamlit` and knows nothing about the
  bridge.

## UI bridge (`app/runner_bridge.py`)

```python
def start_run(text: str, files: list | None = None) -> RunHandle: ...

class RunHandle:
    run_id: str
    def drain_events(self) -> list[AgentEvent]: ...   # thread-safe, non-blocking
    def done(self) -> bool: ...
    def result(self) -> FinalReport | None: ...
    def report_stream(self) -> Iterator[str]: ...     # optional token stream
    def error(self) -> Exception | None: ...
```

### Lifecycle

1. `start_run` validates input (empty/over-length text, PDF readable), generates a
   `run_id`, and launches `Runner.run()` on a **background thread** so the Streamlit
   script thread stays responsive (FR-001).
2. The background thread runs only core code; it pushes events onto a thread-safe
   queue fed by the `EventBus`. It MUST NOT call `st.*` (no `ScriptRunContext`).
3. The UI drains events each fragment tick (`drain_events`) and renders the trace;
   once `done()` is true it reads `result()` / `report_stream()` for the report.

### Guarantees

- `start_run` returns immediately with a `run_id`; it never blocks on completion.
- `drain_events` is non-blocking and returns events in order; a late first call
  replays buffered events (the `TraceStore` backs the queue).
- A single failed source never aborts the run; `done()` still becomes true with a
  partial `FinalReport` (SC-003).
- `result()` is `None` until `done()`; on failure `error()` is set and `done()` is
  true.
- The bridge holds no secrets and contains no agent/LLM/prompt logic (FR-013).

### Input validation (entry point)

- Empty / over-length text → `ValueError`, surfaced as a chat error; no run starts.
- Unreadable / empty PDF → `ValueError`; no run starts (FR-014).

### Readiness

The UI builds the runner via `@st.cache_resource(build_runner)` once per session; a
failed build (e.g. missing `GROQ_API_KEY`) shows an error banner instead of the chat
input.
