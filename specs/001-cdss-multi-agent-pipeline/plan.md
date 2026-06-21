# Implementation Plan: CDSS Multi-Agent Clinical Research Pipeline

**Branch**: `001-cdss-multi-agent-pipeline` | **Date**: 2026-06-21 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/001-cdss-multi-agent-pipeline/spec.md`

## Summary

Port the 5-agent CDSS Colab notebook into a deep-module, event-driven system
delivered as a **single Streamlit application** ("trimlet"). A headless **`cdss/`
core** owns all agents, secrets, and external calls and runs a **LangGraph**
pipeline (intake → research → trials → cross-indication → synthesis) where every
agent is spawned through a single **AgentFactory** that emits a typed event stream.
The **Streamlit `app/`** is a **chat UI**: the patient describes their case in
`st.chat_input` (free text or a PDF), the report streams back into an
`st.chat_message`, and a side panel renders the live agent-trace tree from the
core's in-process event stream — no web server, no REST/SSE (Constitution II). The
LLM is selected at runtime from **Groq's free tier** by a configured preference
order — no hard-coded model. Everything is realized as small, focused modules
(deep modules, narrow interfaces) per the constitution.

The canonical design is captured in [ARCHITECTURE.md](../../ARCHITECTURE.md) — note
its FastAPI/REST/SSE transport is **superseded** by Constitution v2.0.0 (see the
Chat UI Design section below). This plan binds the design to the spec's user
stories and the constitution's gates.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Core (`cdss/`) — LangGraph, Pydantic v2, pydantic-settings, openai (Groq-compatible), httpx (outbound fetch), trafilatura/readability, pypdf, networkx, optional qdrant-client + sentence-transformers, PyYAML. UI (`app/`) — **Streamlit only** (`st.chat_input`, `st.chat_message`, `st.write_stream`, `st.status`, `st.fragment`, `st.cache_resource`); imports the core, holds no HTTP client.  
**Storage**: In-memory per-run trace store + event bus (v1); optional Qdrant for uploaded-PDF vectors; PrimeKG cached on local disk (`/tmp/primekg`). No relational DB in v1.  
**Testing**: pytest + pytest-asyncio; respx/monkeypatch to mock HTTP + LLM; Streamlit `st.testing.AppTest` for UI logic with a stubbed runner (no live agents).  
**Target Platform**: A single `streamlit run app/main.py` process (local or Docker); no uvicorn/web server.  
**Project Type**: Single Streamlit application — headless `cdss/` core + `app/` chat UI in one deployable.  
**Performance Goals**: ~60 s end-to-end on free tier (SC-001); up to N=5 Source-Readers concurrent; trace renders sub-second via a 0.5–1 s `st.fragment` refresh.  
**Constraints**: Free LLM tier (rate-limited) → bounded concurrency + token budgets in config; per-fetch timeout; `cdss/` MUST NOT import `streamlit`; the run executes off the script thread (background thread) so the Streamlit rerun loop stays responsive; files within constitutional size limit.  
**Scale/Scope**: Single-tenant/local-first v1; one run at a time per session; ~9 agent types; 4 LangGraph phases.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan complies |
|-----------|------------------------|
| **I. Deep Modules, Small Files** | Each agent, adapter, and UI component is its own ≤~200-line module behind an ABC/Pydantic interface. `agents/`, `sources/`, `knowledge/`, `pipeline/`, and `app/components/` are packages of leaf modules. A CI file-size check (≤400 lines hard limit) is a quality gate. |
| **II. UI/Core Separation — Streamlit-Only** | One Streamlit app; `app/` imports the headless `cdss/` core through a single `runner_bridge` interface and holds no agent/LLM/prompt/secret logic. `cdss/` MUST NOT import `streamlit`; a CI import-direction guard enforces it. Live updates flow via the in-memory event bus + UI reruns — no FastAPI/REST/SSE. |
| **III. Free-Model-First & Provider Abstraction** | `llm/client.py` queries Groq models at runtime, picks by YAML preference order; single `chat()` interface; budgets/limits in `sources.yaml`. |
| **IV. Factory + Events** | All spawns via `AgentFactory.spawn()`; coordinators delegate, leaves do one unit; adapters live in `sources/`/`knowledge/`/`integrations/`; every step emits a typed event on the per-run bus that the UI renders. |
| **V. Research-Only Safety** | Disclaimer enforced in the synthesizer **and** the persistent UI banner; agents summarize sourced material only; entry-point input validation; untrusted-content handling for fetched pages; PII redaction in logs/events. |
| **VI. Surgical Changes — Minimal Diffs** | Spec/plan/tasks are revised by targeted edits (e.g., this chat-UI upgrade), never wholesale rewrites; any larger rewrite is justified inline. |
| **VII. Short Comments** | Code comments stay one–two sentences; a CI comment-length gate enforces it. |

**Result**: PASS. No violations → Complexity Tracking left empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-cdss-multi-agent-pipeline/
├── spec.md              # Feature spec (what/why)
├── context.md           # Feature context (mission, code paths)
├── plan.md              # This file
├── research.md          # Phase 0 — decisions & rationale
├── data-model.md        # Phase 1 — entities & state
├── quickstart.md        # Phase 1 — run/dev instructions
├── contracts/           # Phase 1 — runner + event + agent contracts
│   ├── runner.md        # UI→core bridge (replaces rest-api.md; realign via /speckit-plan)
│   ├── events.md
│   └── agents.md
└── tasks.md             # Phase 2 — created by /speckit.tasks
```

### Source Code (repository root)

One Streamlit app: a headless `cdss/` core plus an `app/` chat UI. Every leaf
below is a small, single-responsibility file (deep modules, Principle I).

```text
cdss/                               # headless core — NEVER imports streamlit
├── config/                         # settings.py, sources.yaml
├── core/                           # pure domain: enums.py, exceptions.py, models/
├── observability/                  # events.py, event_bus.py, run_context.py, trace_store.py
├── llm/                            # client.py, model_selector.py, json_utils.py, prompts/
├── sources/                        # search/, fetch/, extract/ (adapters, NOT agents)
├── knowledge/                      # graph/ (PrimeKG→NetworkX), vector/ (optional Qdrant)
├── integrations/                   # clinical_trials.py, pubmed.py
├── agents/                         # base.py, factory.py, registry.py + one pkg per agent
└── pipeline/                       # state.py, nodes.py, workflow.py (LangGraph), runner.py

app/                                # Streamlit chat UI — imports cdss/, no agent/LLM logic
├── main.py                         # `streamlit run app/main.py`: page config, layout, wiring
├── runner_bridge.py                # ONLY core touchpoint: start run in bg thread → event queue + result
├── state/session.py                # st.session_state init/helpers (messages, run_id, events, status)
└── components/
    ├── disclaimer.py               # persistent medical-disclaimer banner
    ├── suggestions.py              # suggestion chips (example prompts) before first message
    ├── chat.py                     # st.chat_input(accept_file) + st.chat_message history
    ├── agent_trace.py              # live spawn tree via st.status, refreshed by st.fragment
    ├── report_view.py              # st.tabs(Profile|Standard Care|Trials|Off-Label) + st.write_stream
    └── feedback.py                 # st.feedback("thumbs") on the report (optional)

tests/
├── core/{unit,integration}/        # mirrors cdss/ packages; never imports streamlit
└── app/unit/                       # session, runner_bridge, trace rendering via st.testing.AppTest
```

**Structure Decision**: **Single Streamlit application** — one deployable with a
headless `cdss/` core and an `app/` chat UI, per Constitution II (Streamlit-only,
no FastAPI). The core tree maps to `ARCHITECTURE.md §4` **minus the `api/` layer**;
agents/adapters are focused leaf modules (Principle I) and the UI is decomposed into
small chat components. The notebook's monolithic cells split as before: state →
`core/models/` + `pipeline/state.py`; LLM → `llm/`; KG → `knowledge/graph/`; each
`agent_*` → its own module; the Colab run loop (Cells 30–34) becomes
`pipeline/runner.py` (core) + `app/runner_bridge.py` (UI driver).

## Phasing (maps user stories → build order)

- **Phase 0 — Research** ([research.md](./research.md)): resolve Groq model discovery,
  search provider, in-process event delivery to the UI, PrimeKG load/caching, and the
  non-blocking Streamlit run + `st.fragment` refresh pattern.
- **Phase 1 — Design** ([data-model.md](./data-model.md), [contracts/](./contracts/),
  [quickstart.md](./quickstart.md)): freeze entities, the event / agent / runner
  contracts, and the chat-UI dev workflow.
- **Phase 2 — Tasks** (`/speckit.tasks` → tasks.md): Setup → Foundational (core, config,
  observability, llm, factory) → US1 (intake+research+report MVP) → US2 (live trace) →
  US3 (trials) → US4 (cross-indication) → US5 (PDF) → Polish (retry, caching, rate limit).

Build order honors story priority: **US1 + US2 are the P1 MVP**; US3/US4 are additive P2;
US5 is P3. Foundational phase (factory, event bus, llm client, core models) blocks all
stories and is built once.

## Chat UI Design (Streamlit)

The `app/` layer is a chat interface over the in-process `cdss/` core. It uses
`st.chat_message`/`st.chat_input` for the conversation, `st.session_state` for
history, `st.write_stream` for the streaming report, and `st.status` + `st.fragment`
for the live agent trace. The UI never runs agents itself — it calls
`runner_bridge` (the one core touchpoint) and renders events.

### Layout & session state
- Wide layout. A persistent disclaimer banner (`components/disclaimer.py`) sits at
  the top of every rerun — Principle V.
- Two columns: **left** = chat (history + input), **right** = live agent trace.
  Report tabs render inside the assistant's `st.chat_message`.
- `st.session_state` keys: `messages` (chat history), `run_id`, `events` (trace
  list), `run_status` (`idle|running|completed|failed`), `report`.

### One input for text *and* PDF (US1 + US5)
```python
prompt = st.chat_input("Describe your diagnosis…", accept_file=True, file_type=["pdf"])
if prompt:
    # PDF bytes go to the core extractor — the UI never parses them.
    st.session_state.run_id = runner_bridge.start_run(prompt.text, prompt.files)
    st.rerun()
```

### Non-blocking run + in-process events (FR-001, FR-009)
`runner_bridge.start_run()` launches the async core pipeline on a **background
thread** and returns a handle exposing a thread-safe event queue + a future for the
report. That thread runs only core code — it has no `ScriptRunContext`, so it must
never call `st.*`. The UI drains events in a fragment:
```python
@st.fragment(run_every="0.7s")
def live_trace(handle):
    st.session_state.events.extend(handle.drain_events())
    agent_trace.render(st.session_state.events)      # st.status tree
    if handle.done():
        st.session_state.run_status = "completed"
        st.rerun()                                   # exit fragment → render full report
```

### Agent trace tree (US2) via st.status
`components/agent_trace.py` builds the parent→child tree from events and maps agent
status to `st.status` state — `running→"running"`, `completed→"complete"`,
`failed→"error"`. A timed-out Source-Reader shows `state="error"` without breaking
the run (SC-003). Each node line shows label + duration.

### Streaming the report (FR-007)
If `pipeline/runner.py` exposes the synthesizer as a token generator, stream it;
otherwise render the final markdown. Sections are `st.tabs`:
```python
with st.chat_message("assistant", avatar=":material/clinical_notes:"):
    profile, care, trials, offlabel = st.tabs(["Profile","Standard Care","Trials","Off-Label"])
    with care:
        st.write_stream(handle.report_stream())      # or st.markdown(report.markdown)
    st.caption(DISCLAIMER)                            # disclaimer in every report
    st.feedback("thumbs")                            # optional
```

### Suggestion chips, caching, new case
- **Suggestion chips** (`components/suggestions.py`) show example prompts (e.g. the
  NSCLC case) before the first message; clicking one seeds the run.
- **`st.cache_resource`** builds the runner (Groq `LLMClient`, `AgentFactory`, KG
  loader) once per session so PrimeKG/Groq don't reload each rerun.
- A **"New case"** button resets `messages`/`run_id`/`events`/`run_status` and reruns.

### Testing the UI (no live agents)
`st.testing.AppTest` drives `app/` with a **stubbed `runner_bridge`** (fixture events
+ canned report): assert the disclaimer is present, the trace tree renders (incl. a
failed node), and the report tabs populate. Core agents are never invoked in UI tests
(Constitution II).

### Anti-patterns to avoid
- No agent/LLM/prompt/secret code in `app/` (FR-013); no `st.*` from the background
  thread; never block the main script on the pipeline (always go via the
  fragment/queue); keep each component within the size limit and comments to one–two
  sentences (Principles I & VII).

## Complexity Tracking

> No constitutional violations. Section intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
