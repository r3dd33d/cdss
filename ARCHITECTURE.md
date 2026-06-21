# CDSS — Clinical Decision Support System

## Architecture & Project Layout

> **Baseline:** [CDSS_Pipeline_Colab.ipynb](CDSS_Pipeline_Colab.ipynb) (5-agent research pipeline)
> **Goal:** A production-grade, deep-module **single Streamlit application** with live agent tracing in the chat UI.
> **Governing rules:** [.specify/memory/constitution.md](.specify/memory/constitution.md) (v2.0.0 — Streamlit-only, no FastAPI).
> **Detailed contracts:** [specs/001-cdss-multi-agent-pipeline/](specs/001-cdss-multi-agent-pipeline/) (spec, plan, data-model, contracts, tasks).

> **Note — supersedes the original draft.** An earlier version of this file described a
> FastAPI backend + separate Streamlit frontend talking over REST/SSE. That topology is
> **removed**: per Constitution v2.0.0 this is one Streamlit app whose headless `cdss/`
> core runs the pipeline in-process. This document now reflects that.

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [High-Level Architecture](#2-high-level-architecture)
3. [UI / Core Separation Contract](#3-ui--core-separation-contract)
4. [Complete Directory Layout](#4-complete-directory-layout)
5. [Module Responsibilities](#5-module-responsibilities)
6. [Agent Hierarchy & Factory](#6-agent-hierarchy--factory)
7. [Pipeline Flow](#7-pipeline-flow)
8. [Runner Bridge Interface](#8-runner-bridge-interface)
9. [Chat UI (Streamlit) Specification](#9-chat-ui-streamlit-specification)
10. [Configuration & Environment](#10-configuration--environment)
11. [Observability & Event Model](#11-observability--event-model)
12. [Data Models](#12-data-models)
13. [Implementation Phases](#13-implementation-phases)
14. [Testing Strategy](#14-testing-strategy)
15. [Deployment Topology](#15-deployment-topology)

---

## 1. Design Principles

Mirrors the project constitution; see [constitution.md](.specify/memory/constitution.md) for the authoritative wording.

| # | Principle | Rule |
|---|-----------|------|
| 1 | **Deep modules, small files** | Narrow interfaces over substantial functionality; ≤~200 lines/file (≤400 hard limit). Split by responsibility, not line count. |
| 2 | **UI/Core separation (Streamlit-only)** | The `app/` UI imports the headless `cdss/` core through one `runner_bridge` interface. `cdss/` never imports `streamlit`. No FastAPI/REST/SSE. |
| 3 | **One source = one agent** | Each URL/document gets its own `SourceReaderAgent` for isolated context and parallel execution. |
| 4 | **Coordinators spawn, leaves work** | Coordinator agents plan and delegate; leaf agents fetch, read, and summarize. |
| 5 | **Factory owns spawning** | All agent creation goes through `AgentFactory` — single place for lifecycle + events. |
| 6 | **Adapters ≠ agents** | HTTP, search, PDF parsing live in `sources/` (infrastructure), not inside agent classes. |
| 7 | **Events everywhere** | Every spawn, fetch, LLM call, and failure emits an event for the UI trace panel. |
| 8 | **Free-model-first** | LLM selected at runtime from Groq's free tier by configured preference order; no hard-coded model. |
| 9 | **Config over code** | Allowed sites, search providers, model preference, and limits live in YAML — not hardcoded. |
| 10 | **Surgical changes** | Prefer the smallest edit; change a block only when necessary. Larger rewrites must be justified. |
| 11 | **Short comments** | One or two sentences; comment *why*, not *what*. |
| 12 | **Research only** | All outputs include medical disclaimers. This is not medical advice. |

---

## 2. High-Level Architecture

One process: `streamlit run app/main.py`. The UI drives the in-process core; events
flow back through an in-memory bus — no network boundary.

```
┌─────────────────────────────────────────────────────────────────┐
│                  STREAMLIT APP  (app/)  — UI only                │
│  • st.chat_input (text + PDF)      • live agent trace (st.status) │
│  • st.chat_message history         • report tabs (st.write_stream)│
│  • persistent disclaimer banner                                  │
│  • NO agents · NO LLM · NO prompts · NO secrets · NO streamlit-in-core │
└───────────────┬───────────────────────────────▲─────────────────┘
                │ runner_bridge.start_run()      │ drain_events() / result()
                │ (background thread)            │ (in-process queue)
                ▼                                │
┌─────────────────────────────────────────────────────────────────┐
│                     HEADLESS CORE  (cdss/)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  pipeline/   │→ │  AgentFactory│→ │  agents/ (registry)  │  │
│  │  (LangGraph) │  │  + EventBus  │  │                      │  │
│  └──────────────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         IntakeAgent  ResearchCoordinator  SourceReaderAgents …  │
│                    ┌─────────┴─────────┐                        │
│                    ▼                   ▼                        │
│              sources/            knowledge/                     │
│         (search, fetch)      (graph, vector)                    │
│                    └─────────┬─────────┘                        │
│                              ▼                                   │
│                         llm/ (Groq)                             │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
              External: ClinicalTrials.gov, Serper, PrimeKG, guideline sites
```

### Technology Stack

| Layer | Technology |
|-------|------------|
| App / UI | Streamlit (`st.chat_input`, `st.chat_message`, `st.write_stream`, `st.status`, `st.fragment`, `st.cache_resource`) |
| UI→Core bridge | `app/runner_bridge.py` — background thread + thread-safe event queue (no HTTP) |
| Orchestration | LangGraph |
| LLM | Groq API (DeepSeek R1 distill / Llama fallback), runtime model selection |
| Search | Serper / Tavily / Google CSE (configurable) |
| Graph | NetworkX + PrimeKG |
| Vector (optional) | Qdrant (for uploaded PDFs) |
| Config | pydantic-settings + YAML |
| Events | In-memory `EventBus` + `TraceStore` per run, drained by the UI |

---

## 3. UI / Core Separation Contract

This replaces the old "Frontend/Backend separation." There is no network boundary —
the separation is an **import boundary** inside one app, enforced by CI.

### UI (`app/`) MAY

- Render chat, trace tree, report tabs, disclaimer
- Call `runner_bridge` to start a run and drain events
- Store UI-only state in `st.session_state` (messages, run_id, events, status)
- Display the markdown report and validate user input (empty/over-length message)

### UI (`app/`) MUST NOT

- Import agents, LangGraph, the pipeline, or any `cdss/` internals **other than** `runner_bridge`
- Hold `GROQ_API_KEY`, search keys, or any secret
- Call Groq, ClinicalTrials.gov, or any external API directly
- Contain prompts, LLM logic, agent code, PDF parsing, or KG queries

### Core (`cdss/`) MUST

- Contain all agent/LLM/pipeline/adapter logic behind narrow interfaces
- Own all secrets via environment variables
- Publish typed events to the per-run `EventBus`
- **Never import `streamlit`** (CI import-direction guard enforces this)

### Communication Pattern

```
UI (app/)                              Core (cdss/)
─────────                              ────────────
runner_bridge.start_run(text, files) → build_runner().run(...)  [background thread]
handle.drain_events()                ← EventBus → thread-safe queue
handle.done() / result()             ← FinalReport (or error)
handle.report_stream()               ← optional synthesizer token stream
```

The UI treats the core as a black box behind `runner_bridge`. Replacing Streamlit with
another UI (or adding an API later) requires only a new bridge — zero core changes.
Full contract: [contracts/runner.md](specs/001-cdss-multi-agent-pipeline/contracts/runner.md).

---

## 4. Complete Directory Layout

```
cdss-ds/                                 # project root (single Streamlit app)
│
├── README.md
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt                     # one env: streamlit + core deps
├── Dockerfile                           # entry: streamlit run app/main.py
├── docker-compose.yml                   # app + optional qdrant
├── Makefile
│
├── ARCHITECTURE.md                      # ← this file
├── CDSS_Pipeline_Colab.ipynb            # baseline notebook
│
├── cdss/                                # ═══ HEADLESS CORE — never imports streamlit ═══
│   ├── __init__.py
│   │
│   ├── config/
│   │   ├── settings.py                  # pydantic-settings (env vars)
│   │   └── sources.yaml                 # allowed sites, search/fetch/llm config
│   │
│   ├── core/                            # pure domain — no I/O
│   │   ├── enums.py                     # AgentType, RunStatus, EventType
│   │   ├── exceptions.py
│   │   └── models/                      # patient, source, trial, hypothesis, report
│   │
│   ├── observability/
│   │   ├── events.py                    # AgentSpawned, SourceFetched, … (+ PII redaction)
│   │   ├── event_bus.py                 # per-run pub/sub; thread-safe drain for the UI
│   │   ├── run_context.py               # run_id, parent_id, depth
│   │   └── trace_store.py               # append-only event log per run
│   │
│   ├── llm/
│   │   ├── client.py                    # Groq OpenAI-compatible client, chat()
│   │   ├── model_selector.py            # runtime model discovery + preference order
│   │   ├── json_utils.py                # strip_json_fences
│   │   └── prompts/                     # intake, source_reader, synthesizer, …
│   │
│   ├── sources/                         # infrastructure adapters (NOT agents)
│   │   ├── registry.py                  # load sources.yaml
│   │   ├── search/                      # base, serper, site_scoped
│   │   ├── fetch/                       # base, httpx_fetcher
│   │   └── extract/                     # html, pdf
│   │
│   ├── knowledge/
│   │   ├── graph/                       # loader (PrimeKG→NetworkX), queries (BFS)
│   │   └── vector/                      # store, embedder, ingest (optional Qdrant)
│   │
│   ├── integrations/
│   │   ├── clinical_trials.py           # ClinicalTrials.gov API v2
│   │   └── pubmed.py                    # URL builder (future: fetch)
│   │
│   ├── agents/
│   │   ├── base.py                      # BaseAgent, AgentTask, AgentResult
│   │   ├── factory.py                   # AgentFactory.spawn()
│   │   ├── registry.py                  # AgentType → class map
│   │   ├── intake/                      # intake_agent.py
│   │   ├── research/                    # coordinator, source_reader, aggregator
│   │   ├── trials/                      # trials_agent.py
│   │   ├── cross_indication/            # coordinator, kg_traversal, hypothesis
│   │   └── synthesis/                   # report_agent.py
│   │
│   └── pipeline/
│       ├── state.py                     # PipelineState (LangGraph state)
│       ├── nodes.py                     # thin wrappers calling agents
│       ├── workflow.py                  # LangGraph graph compile
│       └── runner.py                    # build_runner(); async run() + event wiring
│
├── app/                                 # ═══ STREAMLIT UI — imports cdss/ via runner_bridge ═══
│   ├── main.py                          # streamlit run app/main.py: layout + wiring
│   ├── runner_bridge.py                 # ONLY core touchpoint: bg thread + event queue
│   ├── state/
│   │   └── session.py                   # st.session_state init + helpers
│   └── components/
│       ├── disclaimer.py                # persistent medical-disclaimer banner
│       ├── suggestions.py               # suggestion chips (example prompts)
│       ├── chat.py                      # st.chat_input(accept_file) + st.chat_message
│       ├── agent_trace.py               # live spawn tree via st.status (fragment)
│       ├── report_view.py               # st.tabs + st.write_stream
│       └── feedback.py                  # st.feedback("thumbs") (optional)
│
└── tests/
    ├── core/
    │   ├── unit/                        # models, sources, agents, factory, llm, observability
    │   └── integration/                 # pipeline_mvp, event_stream, full_pipeline (mocks)
    └── app/
        └── unit/                        # chat_flow, agent_trace, pdf_upload via st.testing.AppTest
```

---

## 5. Module Responsibilities

### Core (`cdss/`)

| Module | Responsibility |
|--------|----------------|
| `config/` | Environment variables, YAML source registry |
| `core/` | Pure domain models and enums — no side effects |
| `observability/` | Event bus, run tracing, per-run event store |
| `llm/` | Groq client, runtime model selection, prompt templates |
| `sources/` | Web search, HTTP fetch, HTML/PDF extraction |
| `knowledge/` | PrimeKG graph, optional Qdrant vector store |
| `integrations/` | ClinicalTrials.gov and other external APIs |
| `agents/` | All agent logic + factory + registry |
| `pipeline/` | LangGraph workflow wiring and `runner` entry point |

### UI (`app/`)

| Module | Responsibility |
|--------|----------------|
| `runner_bridge.py` | Start runs on a background thread; expose event queue + result (only core touchpoint) |
| `components/` | Streamlit chat/trace/report widgets — display only |
| `state/` | Session-state initialization and UI helpers |

---

## 6. Agent Hierarchy & Factory

### Agent Types

```
AgentType (enum)
├── INTAKE                    # leaf — parse user input
├── RESEARCH_COORDINATOR      # coordinator — search + spawn readers
├── SOURCE_READER             # leaf — fetch 1 URL, summarize for question
├── RESEARCH_AGGREGATOR       # leaf — merge source summaries
├── TRIALS                    # leaf — ClinicalTrials.gov query
├── CROSS_INDICATION_COORD    # coordinator — route KG vs LLM
├── KG_TRAVERSAL              # leaf — PrimeKG BFS
├── HYPOTHESIS                # leaf (optional) — 1 drug rationale
└── REPORT_SYNTHESIZER        # leaf — final markdown report
```

### Spawn Rules

| Parent | Spawns | Parallelism | Condition |
|--------|--------|-------------|-----------|
| Pipeline | `INTAKE` | sequential | always |
| Pipeline | `RESEARCH_COORDINATOR` | sequential | after intake |
| `RESEARCH_COORDINATOR` | N × `SOURCE_READER` | **parallel** | 1 per discovered URL (max 5) |
| `RESEARCH_COORDINATOR` | `RESEARCH_AGGREGATOR` | sequential | after all readers complete |
| Pipeline | `TRIALS` | sequential | after research |
| Pipeline | `CROSS_INDICATION_COORD` | sequential | after trials |
| `CROSS_INDICATION_COORD` | `KG_TRAVERSAL` | sequential | if PrimeKG loaded |
| `CROSS_INDICATION_COORD` | M × `HYPOTHESIS` | parallel (optional) | 1 per drug candidate |
| Pipeline | `REPORT_SYNTHESIZER` | sequential | final step |

### AgentFactory Interface

```python
# cdss/agents/factory.py

class AgentFactory:
    def __init__(self, registry: AgentRegistry, bus: EventBus,
                 llm: LLMClient, sources: SourceRegistry): ...

    async def spawn(self, agent_type: AgentType, task: AgentTask,
                    *, parent_run_id: str | None = None) -> AgentResult:
        """
        1. Generate run_id
        2. Emit AgentSpawned (with parent_run_id for tree)
        3. Instantiate agent from registry
        4. Emit AgentStarted
        5. await agent.run(task, run_context)
        6. Emit AgentCompleted or AgentFailed
        7. Return result
        """
```

Full agent contract: [contracts/agents.md](specs/001-cdss-multi-agent-pipeline/contracts/agents.md).

---

## 7. Pipeline Flow

### LangGraph Top-Level (sequential phases)

```
intake → research → trials → cross_indication → synthesize → END
```

`cross_indication` is skipped when PrimeKG is unavailable; the run still completes.

### Research Phase (internal spawn tree)

```
ResearchCoordinatorAgent
├─ search_site_scoped("{condition} {stage} standard of care") → [url_1 … url_5]
├─ asyncio.gather(SourceReaderAgent(url_1) … (url_5))   ← parallel, bounded
└─ ResearchAggregatorAgent → standard_care_summary + source_summaries[]
```

### Mapping from Colab Notebook

| Notebook Cell | New Module |
|---------------|-----------|
| Cell 6 — state model | `core/models/` + `pipeline/state.py` |
| Cell 8 — LLM setup | `llm/client.py`, `llm/model_selector.py`, `llm/json_utils.py` |
| Cell 6 — PDF→Qdrant (optional) | `knowledge/vector/ingest.py` |
| Cells 14/16 — PrimeKG load + BFS | `knowledge/graph/{loader,queries}.py` |
| Cell 22 — Clinical Trials | `integrations/clinical_trials.py` |
| Agent 1 — Intake | `agents/intake/intake_agent.py` |
| Agent 2 — Standard Care | `agents/research/*` (web search + source readers) |
| Agent 3 — Clinical Trials | `agents/trials/trials_agent.py` |
| Agent 4 — Cross-Indication | `agents/cross_indication/*` |
| Agent 5 — Synthesizer | `agents/synthesis/report_agent.py` |
| Cell 28 — LangGraph compile | `pipeline/workflow.py` |
| Cells 30–34 — Run + display | `pipeline/runner.py` (core) + `app/runner_bridge.py` + `app/main.py` (UI) |

---

## 8. Runner Bridge Interface

The single seam between UI and core (replaces the old REST API). See full contract in
[contracts/runner.md](specs/001-cdss-multi-agent-pipeline/contracts/runner.md).

### Core entry (`cdss/pipeline/runner.py`)

```python
def build_runner(settings: Settings) -> Runner: ...

class Runner:
    async def run(self, raw_input: str, *, is_pdf: bool = False,
                  options: RunOptions | None = None) -> FinalReport: ...
```

### UI bridge (`app/runner_bridge.py`)

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

`start_run` validates input, generates a `run_id`, and launches `Runner.run()` on a
**background thread** so the Streamlit script stays responsive. That thread runs only
core code and pushes events to a thread-safe queue — it never calls `st.*` (it has no
`ScriptRunContext`). A failed source never aborts the run; `done()` still becomes true
with a partial report.

---

## 9. Chat UI (Streamlit) Specification

### Entry point

```bash
streamlit run app/main.py        # single process
```

### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  ⚠️  Research tool only — not medical advice.  [Disclaimer]      │
├─────────────────────────────┬────────────────────────────────────┤
│  CHAT                       │  AGENT ACTIVITY                    │
│  ─────────────────────────  │  ────────────────────────────────  │
│  User: Stage III NSCLC…     │  ▶ IntakeAgent              ✓ 2s  │
│                             │  ▶ ResearchCoordinator      ✓ 0.4s │
│  Assistant:                 │    ├─ SourceReader nccn.org ✓ 4s  │
│  [Report tabs below]        │    ├─ SourceReader esmo.org ✓ 3s  │
│   Profile│Care│Trials│Off…  │    └─ SourceReader nice.org  ✗     │
│  ┌───────────────────────┐  │  ▶ TrialsAgent              ● …   │
│  │ Describe your case… 📎│  │  ○ ReportSynthesizer               │
│  └───────────────────────┘  │                                    │
└─────────────────────────────┴────────────────────────────────────┘
```

### Key patterns

```python
# One input for text + PDF (US1 + US5) — PDF bytes go to the core, not parsed in the UI
prompt = st.chat_input("Describe your diagnosis…", accept_file=True, file_type=["pdf"])
if prompt:
    st.session_state.run_id = runner_bridge.start_run(prompt.text, prompt.files)
    st.rerun()

# Non-blocking trace refresh — drain the in-process event queue each tick
@st.fragment(run_every="0.7s")
def live_trace(handle):
    st.session_state.events.extend(handle.drain_events())
    agent_trace.render(st.session_state.events)        # st.status tree
    if handle.done():
        st.session_state.run_status = "completed"
        st.rerun()                                     # exit fragment → render report

# Report streamed into a chat message, sectioned by tabs, disclaimer always present
with st.chat_message("assistant", avatar=":material/clinical_notes:"):
    profile, care, trials, offlabel = st.tabs(["Profile","Standard Care","Trials","Off-Label"])
    with care:
        st.write_stream(handle.report_stream())        # or st.markdown(report.markdown)
    st.caption(DISCLAIMER)
```

Other UI elements: suggestion chips before the first message, `@st.cache_resource` to
build the runner (Groq client / factory / KG) once per session, a "New case" reset
button, and optional `st.feedback("thumbs")`. The background thread never calls `st.*`.

---

## 10. Configuration & Environment

### `.env.example`

```bash
# Secrets live in the app environment, read only by the core — never in app/ UI code.
GROQ_API_KEY=gsk_...
SERPER_API_KEY=...
CLINICAL_TRIALS_BASE_URL=https://clinicaltrials.gov/api/v2/studies

# Optional
QDRANT_URL=http://localhost:6333
PRIMEKG_CACHE_DIR=/tmp/primekg
LOG_LEVEL=INFO
```

### `cdss/config/sources.yaml`

```yaml
sites:
  - { id: nccn, domain: nccn.org,     priority: 1, enabled: true }
  - { id: esmo, domain: esmo.org,     priority: 1, enabled: true }
  - { id: nci,  domain: cancer.gov,   priority: 2, enabled: true }
  - { id: nice, domain: nice.org.uk,  priority: 2, enabled: true }
  - { id: asco, domain: asco.org,     priority: 3, enabled: false }   # toggle, no code change

search:
  provider: serper          # serper | tavily | google_cse
  top_k_per_site: 1
  max_total_sources: 5
  query_template: "{condition} {stage} standard of care treatment guidelines"

fetch:
  timeout_seconds: 15
  max_content_chars: 12000
  user_agent: "CDSS-ResearchBot/0.1"

llm:
  provider: groq
  max_tokens_intake: 1024
  max_tokens_source_reader: 1024
  max_tokens_synthesizer: 4096
  model_preference:
    - deepseek-r1-distill-llama-70b
    - llama-3.3-70b-versatile
```

---

## 11. Observability & Event Model

### Event Types

| EventType | When | Payload |
|-----------|------|---------|
| `RUN_STARTED` | Pipeline begins | `run_id`, `input_preview` |
| `AGENT_SPAWNED` | Factory creates agent | `agent_type`, `parent_run_id`, `label` |
| `AGENT_STARTED` | Agent.run() begins | `agent_type`, `run_id` |
| `SOURCE_DISCOVERED` | Search returns URL | `url`, `title`, `site_id`, `rank` |
| `SOURCE_FETCHED` | HTTP fetch complete | `url`, `char_count`, `duration_ms` |
| `LLM_CALL` | LLM request sent | `agent_type`, `prompt_tokens_est` |
| `AGENT_COMPLETED` | Agent.run() success | `agent_type`, `duration_ms`, `summary_preview` |
| `AGENT_FAILED` | Agent.run() exception | `agent_type`, `error` |
| `PHASE_COMPLETED` | LangGraph node done | `phase`, `duration_ms` |
| `RUN_COMPLETED` | Full pipeline done | `run_id`, `total_duration_ms` |
| `RUN_FAILED` | Unrecoverable error | `run_id`, `error` |

Events carry no secrets or raw patient text (PII-redacted). The UI builds the trace
tree from `parent_run_id`; `agent_trace.py` maps status to `st.status` state. Full
event contract: [contracts/events.md](specs/001-cdss-multi-agent-pipeline/contracts/events.md).

### Trace Tree Example

```
run_abc123                          RUN_STARTED
├── agent_intake_001                INTAKE           2.1s ✓
├── agent_research_coord_002        RESEARCH_COORD   0.4s ✓
│   ├── agent_reader_003            SOURCE_READER    4.2s ✓  nccn.org/…
│   ├── agent_reader_004            SOURCE_READER    3.8s ✓  esmo.org/…
│   ├── agent_reader_006            SOURCE_READER    15s  ✗  timeout
│   └── agent_reader_007            SOURCE_READER    3.5s ✓  asco.org/…
├── agent_research_agg_008          RESEARCH_AGG     1.2s ✓
├── agent_trials_009                TRIALS           2.0s ✓
├── agent_cross_coord_010           CROSS_IND_COORD  6.3s ✓
└── agent_synth_011                 REPORT_SYNTH     1.8s ✓
                                    RUN_COMPLETED    26.6s
```

---

## 12. Data Models

Pure-domain Pydantic v2 models in `cdss/core/models/`; LangGraph state in
`cdss/pipeline/state.py`. The UI consumes these directly through `runner_bridge` — there
is no separate wire-DTO layer. Full detail:
[data-model.md](specs/001-cdss-multi-agent-pipeline/data-model.md).

### PipelineState (LangGraph shared state)

```python
class PipelineState(BaseModel):
    run_id: str
    raw_input: str
    input_is_pdf: bool = False
    # intake (Agent 1)
    condition: str = ""
    stage: str = ""
    biomarkers: list[Biomarker] = []
    current_medications: list[str] = []
    prior_therapies: list[str] = []
    # research (Agent 2)
    source_summaries: list[SourceSummary] = []
    standard_care_summary: str = ""
    # trials (Agent 3)
    clinical_trials: list[ClinicalTrial] = []
    # cross-indication (Agent 4)
    off_label_hypotheses: list[OffLabelHypothesis] = []
    # synthesis (Agent 5)
    validation_flags: list[str] = []
    final_report: str = ""
    # control (notebook retry rule)
    retry_count: int = 0
    max_retries: int = 2
```

### SourceSummary (per-source agent output)

```python
class SourceSummary(BaseModel):
    source: SourceRef          # url, title, site_id
    relevant_excerpt: str      # LLM summary scoped to patient question
    confidence: float          # 0.0–1.0 heuristic
    fetch_duration_ms: int
    agent_run_id: str          # links to trace tree
```

---

## 13. Implementation Phases

Detailed, dependency-ordered tasks live in
[tasks.md](specs/001-cdss-multi-agent-pipeline/tasks.md). Summary:

### Phase 0 — Setup
- [ ] Single-app skeleton (`cdss/` + `app/` + `tests/`)
- [ ] `pyproject.toml` / `requirements.txt` (streamlit + core deps; no fastapi/uvicorn)
- [ ] CI gates: file-size, import-direction (`cdss/` ⊬ `streamlit`), comment-length
- [ ] Dockerfile (`streamlit run app/main.py`) + compose (app + optional qdrant)

### Phase 1 — Foundational
- [ ] `core/models`, `config/settings`, `observability/` (events, bus, trace store)
- [ ] `llm/client.py` + runtime model selection
- [ ] `AgentFactory` + `AgentRegistry` + event emission, with unit tests

### Phase 2 — US1 + US2 (P1 MVP)
- [ ] `sources/` adapters; Intake, SourceReader, Coordinator, Aggregator, Synthesizer
- [ ] `pipeline/runner.py` + `app/runner_bridge.py` (non-blocking run)
- [ ] Chat UI: disclaimer, chat input, report tabs, live `st.status` trace via fragment

### Phase 3 — US3 / US4 / US5
- [ ] Trials agent (CT.gov); Cross-indication + PrimeKG (graceful skip); PDF upload via chat

### Phase 4 — Polish
- [ ] `st.cache_resource` runner, "New case", feedback; source caching; rate/size limits
- [ ] Full end-to-end integration test with partial source failures

---

## 14. Testing Strategy

### Core (`cdss/`)

| Layer | What to test | How |
|-------|-------------|-----|
| `core/models` | Validation, serialization | Unit |
| `sources/*` | Query building, fetch timeout, extraction | Unit, mocked HTTP |
| `agents/source_reader` | Prompt → summary | Unit, mocked LLM |
| `agents/factory` | Spawn events, parent/child tree | Unit |
| `pipeline/runner` | Full run, retry rule, partial failures | Integration, all mocks |
| `observability/event_bus` | Publish/drain, ordering, cross-thread | Unit |

### UI (`app/`)

| Layer | What to test | How |
|-------|-------------|-----|
| `runner_bridge` | start/drain/done/result against a fake runner | Unit |
| `components/agent_trace` | Tree rendering from event list (incl. failed node) | `st.testing.AppTest` |
| `state/session` | State initialization | Unit |

**Rule:** Core tests never import `streamlit`; UI tests never run real agents (they stub
`runner_bridge`). No test hits a live external service or the free Groq quota.

---

## 15. Deployment Topology

### Development

```
streamlit run app/main.py   →  http://localhost:8501  (single process)
```

### Production (Docker Compose)

```yaml
services:
  app:
    build: .
    command: streamlit run app/main.py --server.port 8501 --server.address 0.0.0.0
    ports: ["8501:8501"]
    env_file: .env
    volumes:
      - primekg_cache:/tmp/primekg

  qdrant:          # optional, for uploaded-PDF vectors
    image: qdrant/qdrant
    ports: ["6333:6333"]
```

### Future: swap or extend the UI

Because the UI talks to the core only through `runner_bridge`, you can replace Streamlit
or add an API later by writing a new bridge over the same `Runner` — zero core changes.

---

## Appendix A — Makefile Targets

```makefile
.PHONY: run test lint guards docker-up

run:
	streamlit run app/main.py

test:
	pytest tests/core tests/app -v

lint:
	ruff check . && black --check .

guards:                       # constitution gates
	python scripts/check_file_size.py cdss app          # ≤400 lines
	! grep -rqE '^\s*import streamlit|from streamlit' cdss/   # core ⊬ streamlit
	python scripts/check_comment_length.py cdss app     # ≤2 sentences

docker-up:
	docker compose up --build
```

---

## Appendix B — Medical Disclaimer (required in all outputs)

Every report and the Streamlit UI must display:

> **This tool is for research and education only. It is not medical advice.**
> Clinical trial eligibility must be confirmed by a qualified physician.
> Off-label therapy hypotheses require evaluation by your specialist.
> Never start, stop, or change treatment based on this report alone.

---

## Appendix C — Import-Direction Guard

The core must stay headless. Enforce in CI that `cdss/` never imports `streamlit`:

```bash
# Fails the build if the core depends on the UI framework (Constitution II)
! grep -rnE '^\s*(import streamlit|from streamlit)' cdss/
```

Optionally assert in `app/` startup that no agent/LLM module is imported outside
`runner_bridge`, so UI code cannot bypass the bridge.

---

*Document version: 1.0.0 — 2026-06-21 — aligned with Constitution v2.0.0 (Streamlit-only).*
