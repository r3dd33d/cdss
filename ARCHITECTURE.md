# CDSS — Clinical Decision Support System

## Architecture & Project Layout

> **Baseline:** [CDSS_Pipeline_Colab.ipynb](../../../CDSS_Pipeline_Colab.ipynb) (5-agent research pipeline)  
> **Goal:** Production-grade, scalable multi-agent system with live agent tracing in the UI.

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Frontend / Backend Separation Contract](#3-frontend--backend-separation-contract)
4. [Complete Directory Layout](#4-complete-directory-layout)
5. [Module Responsibilities](#5-module-responsibilities)
6. [Agent Hierarchy & Factory](#6-agent-hierarchy--factory)
7. [Pipeline Flow](#7-pipeline-flow)
8. [Backend API Specification](#8-backend-api-specification)
9. [Frontend (Streamlit) Specification](#9-frontend-streamlit-specification)
10. [Configuration & Environment](#10-configuration--environment)
11. [Observability & Event Model](#11-observability--event-model)
12. [Data Models](#12-data-models)
13. [Implementation Phases](#13-implementation-phases)
14. [Testing Strategy](#14-testing-strategy)
15. [Deployment Topology](#15-deployment-topology)

---

## 1. Design Principles

| # | Principle | Rule |
|---|-----------|------|
| 1 | **Strict FE/BE split** | The frontend never imports backend code, never calls LLMs, never spawns agents, never holds API keys. |
| 2 | **One source = one agent** | Each URL/document gets its own `SourceReaderAgent` for isolated context and parallel execution. |
| 3 | **Coordinators spawn, leaves work** | Coordinator agents plan and delegate; leaf agents fetch, read, and summarize. |
| 4 | **Factory owns spawning** | All agent creation goes through `AgentFactory` — single place for lifecycle + events. |
| 5 | **Adapters ≠ agents** | HTTP, search, PDF parsing live in `sources/` (infrastructure), not inside agent classes. |
| 6 | **Events everywhere** | Every spawn, fetch, LLM call, and failure emits an event for the UI trace panel. |
| 7 | **Config over code** | Allowed sites, search providers, and limits live in YAML — not hardcoded in agents. |
| 8 | **Research only** | All outputs include medical disclaimers. This is not medical advice. |

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Streamlit)                      │
│  • Chat input                                                    │
│  • Agent activity trace (live via SSE/WebSocket)                 │
│  • Report viewer                                                 │
│  • NO business logic · NO LLM · NO agent code · NO secrets       │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP REST + SSE (or WebSocket)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  API Layer   │→ │   Pipeline   │→ │   Agent Factory      │  │
│  │  (routers)   │  │  (LangGraph) │  │   + Registry         │  │
│  └──────────────┘  └──────────────┘  └──────────┬───────────┘  │
│                                                  │ spawn        │
│         ┌────────────────────────────────────────┼──────────┐  │
│         ▼                    ▼                   ▼          ▼  │
│   IntakeAgent    ResearchCoordinator    SourceReaderAgents  …  │
│         │                    │                   │              │
│         └────────────────────┴───────────────────┘              │
│                              │                                   │
│                    ┌─────────┴─────────┐                        │
│                    ▼                   ▼                        │
│              sources/            knowledge/                     │
│         (search, fetch)      (graph, vector)                    │
│                    │                   │                        │
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
| Frontend | Streamlit, `httpx` or `requests` (API client only), optional `streamlit-chat` |
| Backend API | FastAPI, Uvicorn |
| Orchestration | LangGraph |
| LLM | Groq API (DeepSeek R1 / Llama fallback) |
| Search | Serper / Tavily / Google CSE (configurable) |
| Graph | NetworkX + PrimeKG |
| Vector (fallback) | Qdrant (optional, for uploaded PDFs) |
| Config | pydantic-settings + YAML |
| Events | In-memory EventBus + SSE stream to frontend |

---

## 3. Frontend / Backend Separation Contract

### Frontend MAY

- Render UI components (chat, trace tree, report tabs)
- Call backend REST endpoints
- Subscribe to SSE/WebSocket for live events
- Store UI-only state in `st.session_state` (messages, selected tab, run_id)
- Display markdown reports returned by the API
- Handle user input validation (empty message, max length)

### Frontend MUST NOT

- Import anything from `backend/` or `cdss/` package
- Hold `GROQ_API_KEY`, search API keys, or any secret
- Call Groq, OpenAI, ClinicalTrials.gov, or any external API directly
- Instantiate agents, LangGraph, or pipeline runners
- Contain prompts, LLM logic, or agent factory code
- Parse PDFs, scrape websites, or run knowledge graph queries

### Backend MUST

- Expose all functionality via documented HTTP endpoints
- Stream agent events to the frontend in real time
- Own all secrets via environment variables
- Return structured JSON + markdown report payloads
- Enforce rate limits and input sanitization

### Communication Pattern

```
Frontend                          Backend
────────                          ───────
POST /api/v1/runs                 → start pipeline, return run_id
GET  /api/v1/runs/{id}/events     → SSE stream of agent events
GET  /api/v1/runs/{id}            → poll run status + final report
GET  /api/v1/health               → liveness check
```

The frontend treats the backend as a **black box**. Replacing Streamlit with React later requires zero backend changes.

---

## 4. Complete Directory Layout

```
cdss/                                    # Project root (standalone repo or monorepo subfolder)
│
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml                   # backend + optional qdrant
├── Makefile                             # dev shortcuts
│
├── docs/
│   ├── ARCHITECTURE.md                    # ← this file
│   ├── API.md                             # OpenAPI-derived endpoint docs
│   └── AGENTS.md                          # agent catalog & spawn rules
│
├── backend/                               # ═══ BACKEND ONLY ═══
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── Dockerfile
│   │
│   └── cdss/                              # Python package
│       ├── __init__.py
│       │
│       ├── main.py                        # FastAPI app entry: uvicorn cdss.main:app
│       │
│       ├── api/                           # HTTP layer — thin, no business logic
│       │   ├── __init__.py
│       │   ├── deps.py                    # DI: factory, settings, event bus
│       │   ├── routers/
│       │   │   ├── health.py
│       │   │   ├── runs.py                # POST /runs, GET /runs/{id}
│       │   │   └── events.py              # GET /runs/{id}/events (SSE)
│       │   └── schemas/
│       │       ├── requests.py            # CreateRunRequest
│       │       ├── responses.py           # RunResponse, RunStatusResponse
│       │       └── events.py              # AgentEventDTO (API-facing)
│       │
│       ├── config/
│       │   ├── settings.py                # pydantic-settings (env vars)
│       │   └── sources.yaml               # allowed sites, search config
│       │
│       ├── core/                          # Domain models — pure Python, no I/O
│       │   ├── __init__.py
│       │   ├── enums.py                   # AgentType, RunStatus, EventType
│       │   ├── exceptions.py
│       │   └── models/
│       │       ├── patient.py             # Biomarker, PatientProfile
│       │       ├── source.py              # SourceRef, SourceSummary
│       │       ├── trial.py               # ClinicalTrial
│       │       ├── hypothesis.py          # OffLabelHypothesis
│       │       └── report.py              # FinalReport
│       │
│       ├── observability/
│       │   ├── __init__.py
│       │   ├── events.py                  # AgentSpawned, SourceFetched, ...
│       │   ├── event_bus.py               # pub/sub per run_id
│       │   ├── run_context.py             # run_id, parent_id, depth
│       │   └── trace_store.py             # append-only event log per run
│       │
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── client.py                  # Groq OpenAI-compatible client
│       │   ├── model_selector.py          # preference order from notebook
│       │   ├── json_utils.py              # strip_json_fences
│       │   └── prompts/
│       │       ├── intake.py
│       │       ├── source_reader.py
│       │       ├── standard_care.py
│       │       ├── cross_indication.py
│       │       └── synthesizer.py
│       │
│       ├── sources/                       # Infrastructure adapters (NOT agents)
│       │   ├── __init__.py
│       │   ├── registry.py                # load sources.yaml
│       │   ├── search/
│       │   │   ├── base.py                # AbstractSearchProvider
│       │   │   ├── serper.py
│       │   │   ├── tavily.py
│       │   │   └── site_scoped.py         # site:nccn.org OR site:esmo.org
│       │   ├── fetch/
│       │   │   ├── base.py                # AbstractFetcher
│       │   │   ├── httpx_fetcher.py
│       │   │   └── pdf_fetcher.py
│       │   └── extract/
│       │       ├── html.py                # trafilatura / readability
│       │       └── pdf.py                 # pypdf
│       │
│       ├── knowledge/
│       │   ├── __init__.py
│       │   ├── graph/
│       │   │   ├── loader.py              # PrimeKG → NetworkX
│       │   │   └── queries.py             # find_drugs_for_gene, BFS
│       │   └── vector/
│       │       ├── store.py               # Qdrant abstraction
│       │       ├── embedder.py            # BioBERT sentence-transformers
│       │       └── ingest.py              # PDF chunk + upsert
│       │
│       ├── integrations/
│       │   ├── __init__.py
│       │   ├── clinical_trials.py         # ClinicalTrials.gov API v2
│       │   └── pubmed.py                  # URL builder (future: fetch)
│       │
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── base.py                    # BaseAgent, AgentTask, AgentResult
│       │   ├── factory.py                 # AgentFactory.spawn()
│       │   ├── registry.py                # AgentType → class map
│       │   │
│       │   ├── intake/
│       │   │   └── intake_agent.py        # Notebook Agent 1
│       │   │
│       │   ├── research/                  # Replaces notebook Agent 2
│       │   │   ├── coordinator_agent.py   # search → spawn readers
│       │   │   ├── source_reader_agent.py # 1 URL → 1 summary (LEAF)
│       │   │   └── aggregator_agent.py    # merge summaries → standard care
│       │   │
│       │   ├── trials/
│       │   │   └── trials_agent.py        # Notebook Agent 3
│       │   │
│       │   ├── cross_indication/
│       │   │   ├── coordinator_agent.py   # KG route vs LLM fallback
│       │   │   ├── kg_traversal_agent.py  # PrimeKG BFS
│       │   │   └── hypothesis_agent.py    # optional: 1 drug → 1 agent
│       │   │
│       │   └── synthesis/
│       │       └── report_agent.py        # Notebook Agent 5
│       │
│       └── pipeline/
│           ├── __init__.py
│           ├── state.py                   # PipelineState (LangGraph state)
│           ├── nodes.py                   # thin wrappers calling agents
│           ├── workflow.py                # LangGraph graph compile
│           └── runner.py                  # async invoke + event wiring
│
├── frontend/                              # ═══ FRONTEND ONLY ═══
│   ├── pyproject.toml                     # separate deps (streamlit, httpx)
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .streamlit/
│   │   └── config.toml                    # theme, server port
│   │
│   └── app/
│       ├── main.py                        # streamlit run app/main.py
│       │
│       ├── api_client/                  # ONLY way to talk to backend
│       │   ├── __init__.py
│       │   ├── client.py                  # CDSSApiClient class
│       │   ├── models.py                  # FE DTOs (mirror API responses)
│       │   └── sse.py                     # SSE event stream reader
│       │
│       ├── components/
│       │   ├── __init__.py
│       │   ├── chat.py                    # message input + history display
│       │   ├── agent_trace.py             # live run tree / timeline
│       │   ├── report_view.py             # markdown report tabs
│       │   ├── run_status.py              # progress indicator
│       │   └── disclaimer.py              # static medical disclaimer banner
│       │
│       ├── pages/
│       │   └── history.py                 # past runs list (optional v2)
│       │
│       └── state/
│           └── session.py                 # st.session_state init + helpers
│
└── tests/
    ├── backend/
    │   ├── unit/
    │   │   ├── agents/
    │   │   │   ├── test_factory.py
    │   │   │   ├── test_source_reader.py
    │   │   │   └── test_intake.py
    │   │   ├── sources/
    │   │   │   ├── test_site_scoped_search.py
    │   │   │   └── test_html_extract.py
    │   │   └── pipeline/
    │   │       └── test_state.py
    │   └── integration/
    │       ├── test_api_runs.py
    │       └── test_pipeline_smoke.py
    │
    └── frontend/
        └── unit/
            ├── test_api_client.py         # mock backend responses
            └── test_session.py
```

---

## 5. Module Responsibilities

### Backend

| Module | Responsibility |
|--------|----------------|
| `api/` | HTTP routing, request validation, response serialization, SSE streaming |
| `config/` | Environment variables, YAML source registry |
| `core/` | Pure domain models and enums — no side effects |
| `observability/` | Event bus, run tracing, per-run event store |
| `llm/` | Groq client, model selection, prompt templates |
| `sources/` | Web search, HTTP fetch, HTML/PDF extraction |
| `knowledge/` | PrimeKG graph, optional Qdrant vector store |
| `integrations/` | ClinicalTrials.gov and other external APIs |
| `agents/` | All agent logic + factory + registry |
| `pipeline/` | LangGraph workflow wiring and runner |

### Frontend

| Module | Responsibility |
|--------|----------------|
| `api_client/` | HTTP calls to backend, SSE subscription, response parsing |
| `components/` | Streamlit UI widgets — display only |
| `state/` | Session state initialization and UI helpers |
| `pages/` | Optional multi-page Streamlit routes |

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
# backend/cdss/agents/factory.py

class AgentFactory:
    def __init__(
        self,
        registry: AgentRegistry,
        bus: EventBus,
        llm: LLMClient,
        sources: SourceRegistry,
    ): ...

    async def spawn(
        self,
        agent_type: AgentType,
        task: AgentTask,
        *,
        parent_run_id: str | None = None,
    ) -> AgentResult:
        """
        1. Generate run_id
        2. Emit AgentSpawned event (with parent_run_id for tree)
        3. Instantiate agent from registry
        4. Emit AgentStarted
        5. await agent.run(task, run_context)
        6. Emit AgentCompleted or AgentFailed
        7. Return result
        """
```

### SourceReaderAgent (core leaf agent)

**Input:** `SourceReaderTask`
- `question: str` — the user's research question
- `condition: str`
- `stage: str`
- `source: SourceRef` — `{ url, title, site_id, rank }`

**Steps:**
1. `fetcher.fetch(url)` → raw bytes
2. `extractor.extract(raw)` → plain text
3. `llm.chat(SOURCE_READER_PROMPT)` → relevant summary only
4. Return `SourceSummary { source, excerpt, confidence }`

**Prompt rule:** Summarize ONLY information relevant to the patient's condition/stage/question. Do not invent doses or recommendations.

---

## 7. Pipeline Flow

### LangGraph Top-Level (sequential phases)

```
intake → research → trials → cross_indication → synthesize → END
```

### Research Phase (internal spawn tree)

```
ResearchCoordinatorAgent
│
├─ search_site_scoped("{condition} {stage} standard of care")
│     → [url_1, url_2, url_3, url_4, url_5]
│
├─ asyncio.gather(
│     SourceReaderAgent(url_1),   ← parallel
│     SourceReaderAgent(url_2),
│     SourceReaderAgent(url_3),
│     SourceReaderAgent(url_4),
│     SourceReaderAgent(url_5),
│   )
│
└─ ResearchAggregatorAgent
      → standard_care_summary + source_summaries[]
```

### Mapping from Colab Notebook

| Notebook Cell | New Backend Module |
|---------------|-------------------|
| Cell 6 — PDF upload to Qdrant | `knowledge/vector/ingest.py` (optional fallback) |
| Cell 7 — PrimeKG load | `knowledge/graph/loader.py` |
| Agent 1 — Intake | `agents/intake/intake_agent.py` |
| Agent 2 — Standard Care (Qdrant RAG) | `agents/research/*` (web search + source readers) |
| Agent 3 — Clinical Trials | `agents/trials/trials_agent.py` |
| Agent 4 — Cross-Indication | `agents/cross_indication/*` |
| Agent 5 — Synthesizer | `agents/synthesis/report_agent.py` |
| Cell 14 — LangGraph compile | `pipeline/workflow.py` |
| Cell 15–17 — Run + display | Backend `pipeline/runner.py` + Frontend `app/main.py` |

---

## 8. Backend API Specification

### `POST /api/v1/runs`

Start a new research pipeline run.

**Request:**
```json
{
  "message": "I am a 54-year-old with stage III NSCLC, EGFR exon 19 deletion...",
  "options": {
    "include_trials": true,
    "include_cross_indication": true,
    "max_sources": 5
  }
}
```

**Response `202 Accepted`:**
```json
{
  "run_id": "run_abc123",
  "status": "running",
  "events_url": "/api/v1/runs/run_abc123/events",
  "status_url": "/api/v1/runs/run_abc123"
}
```

### `GET /api/v1/runs/{run_id}`

Poll run status and retrieve final report when complete.

**Response (running):**
```json
{
  "run_id": "run_abc123",
  "status": "running",
  "phase": "research",
  "started_at": "2026-06-20T10:00:00Z"
}
```

**Response (completed):**
```json
{
  "run_id": "run_abc123",
  "status": "completed",
  "phase": "done",
  "started_at": "2026-06-20T10:00:00Z",
  "completed_at": "2026-06-20T10:00:45Z",
  "report": {
    "markdown": "# Patient Research Report\n...",
    "profile": { "condition": "NSCLC", "stage": "III", "biomarkers": [...] },
    "sources": [{ "url": "https://...", "title": "..." }],
    "trials_count": 4,
    "hypotheses_count": 3
  },
  "validation_flags": []
}
```

### `GET /api/v1/runs/{run_id}/events`

Server-Sent Events stream of agent activity.

**Event format:**
```
event: agent_spawned
data: {"run_id":"evt_001","parent_run_id":"run_abc123","agent_type":"SOURCE_READER","label":"Reading nccn.org/...","timestamp":"..."}

event: agent_completed
data: {"run_id":"evt_001","agent_type":"SOURCE_READER","duration_ms":4200,"timestamp":"..."}

event: run_completed
data: {"run_id":"run_abc123","status":"completed","timestamp":"..."}
```

### `GET /api/v1/health`

```json
{ "status": "ok", "version": "0.1.0" }
```

---

## 9. Frontend (Streamlit) Specification

### Entry Point

```bash
# Terminal 1 — backend
cd backend && uvicorn cdss.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && streamlit run app/main.py --server.port 8501
```

Environment variable for frontend:
```
CDSS_API_URL=http://localhost:8000
```

### UI Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  ⚠️  Research tool only — not medical advice.  [Disclaimer]      │
├─────────────────────────────┬────────────────────────────────────┤
│  CHAT                       │  AGENT ACTIVITY                    │
│  ─────────────────────────  │  ────────────────────────────────  │
│                             │                                    │
│  User:                      │  ▶ IntakeAgent              ✓ 2s  │
│  Stage III NSCLC, EGFR...   │  ▶ ResearchCoordinator      ✓ 0.4s │
│                             │    ├─ SourceReader nccn.org ✓ 4s  │
│  Assistant:                 │    ├─ SourceReader esmo.org ✓ 3s  │
│  [Report rendered below]    │    ├─ SourceReader cancer.gov ✓ 5s│
│                             │    └─ SourceReader nice.org.uk ✗   │
│  ┌───────────────────────┐  │  ▶ ResearchAggregator       ✓ 1s  │
│  │ Type your message...  │  │  ▶ TrialsAgent              ✓ 2s  │
│  └───────────────────────┘  │  ▶ CrossIndicationCoord     ● ... │
│  [Send]                     │  ○ ReportSynthesizer               │
├─────────────────────────────┴────────────────────────────────────┤
│  REPORT TABS:  Profile | Standard Care | Trials | Off-Label     │
└──────────────────────────────────────────────────────────────────┘
```

### Frontend API Client (only backend touchpoint)

```python
# frontend/app/api_client/client.py

class CDSSApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def start_run(self, message: str, options: dict | None = None) -> StartRunResponse:
        """POST /api/v1/runs"""

    def get_run(self, run_id: str) -> RunStatusResponse:
        """GET /api/v1/runs/{run_id}"""

    def stream_events(self, run_id: str) -> Iterator[AgentEvent]:
        """GET /api/v1/runs/{run_id}/events — SSE parser"""

    def health(self) -> bool:
        """GET /api/v1/health"""
```

### Frontend Run Loop (in `main.py`)

```python
# Pseudocode — frontend only orchestrates UI, not agents

if user_submits_message:
    response = api_client.start_run(message)
    st.session_state.current_run_id = response.run_id
    st.session_state.events = []

# Background: consume SSE, append to st.session_state.events, st.rerun()

if run_complete:
    result = api_client.get_run(run_id)
    display_report(result.report.markdown)
```

---

## 10. Configuration & Environment

### `.env.example`

```bash
# ── Backend only (never in frontend) ──
GROQ_API_KEY=gsk_...
SERPER_API_KEY=...
CLINICAL_TRIALS_BASE_URL=https://clinicaltrials.gov/api/v2/studies

# Optional
QDRANT_URL=http://localhost:6333
PRIMEKG_CACHE_DIR=/tmp/primekg
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:8501

# ── Frontend only ──
CDSS_API_URL=http://localhost:8000
```

### `backend/cdss/config/sources.yaml`

```yaml
sites:
  - id: nccn
    domain: nccn.org
    priority: 1
    enabled: true
  - id: esmo
    domain: esmo.org
    priority: 1
    enabled: true
  - id: nci
    domain: cancer.gov
    priority: 2
    enabled: true
  - id: nice
    domain: nice.org.uk
    priority: 2
    enabled: true
  - id: asco
    domain: asco.org
    priority: 3
    enabled: false          # toggle without code change

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

### Trace Tree Example

```
run_abc123                          RUN_STARTED
├── agent_intake_001                INTAKE           2.1s ✓
├── agent_research_coord_002        RESEARCH_COORD   0.4s ✓
│   ├── agent_reader_003            SOURCE_READER    4.2s ✓  nccn.org/...
│   ├── agent_reader_004            SOURCE_READER    3.8s ✓  esmo.org/...
│   ├── agent_reader_005            SOURCE_READER    5.1s ✓  cancer.gov/...
│   ├── agent_reader_006            SOURCE_READER    15s  ✗  timeout
│   └── agent_reader_007            SOURCE_READER    3.5s ✓  asco.org/...
├── agent_research_agg_008          RESEARCH_AGG     1.2s ✓
├── agent_trials_009                TRIALS           2.0s ✓
├── agent_cross_coord_010           CROSS_IND_COORD  6.3s ✓
└── agent_synth_011                 REPORT_SYNTH     1.8s ✓
                                    RUN_COMPLETED    26.6s
```

---

## 12. Data Models

### PipelineState (LangGraph shared state)

```python
class PipelineState(BaseModel):
    # run metadata
    run_id: str
    raw_input: str

    # intake (Agent 1)
    condition: str = ""
    stage: str = ""
    biomarkers: list[Biomarker] = []
    current_medications: list[str] = []
    prior_therapies: list[str] = []

    # research (Agent 2 — new shape)
    source_summaries: list[SourceSummary] = []
    standard_care_summary: str = ""

    # trials (Agent 3)
    clinical_trials: list[ClinicalTrial] = []

    # cross-indication (Agent 4)
    off_label_hypotheses: list[OffLabelHypothesis] = []

    # synthesis (Agent 5)
    validation_flags: list[str] = []
    final_report: str = ""

    # control
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

### Phase 0 — Scaffold (Week 1)

- [ ] Create directory structure (backend + frontend)
- [ ] `pyproject.toml` / `requirements.txt` for both
- [ ] FastAPI health endpoint
- [ ] Streamlit shell with API client stub
- [ ] Docker Compose (backend + frontend)
- [ ] Verify frontend cannot import backend package

### Phase 1 — Core Infrastructure (Week 1–2)

- [ ] `core/models`, `config/settings`, `observability/events`
- [ ] `llm/client.py` with Groq model selection
- [ ] `sources/search/site_scoped.py` + `sources/fetch/httpx_fetcher.py`
- [ ] `AgentFactory` + `AgentRegistry` + event emission
- [ ] Unit tests for factory and event bus

### Phase 2 — Source Reader Pipeline (Week 2)

- [ ] `SourceReaderAgent` (leaf)
- [ ] `ResearchCoordinatorAgent` (spawn N readers in parallel)
- [ ] `ResearchAggregatorAgent`
- [ ] `POST /runs` + SSE events endpoint
- [ ] Frontend: chat input + live agent trace panel

### Phase 3 — Port Remaining Notebook Agents (Week 3)

- [ ] `IntakeAgent` (from notebook Agent 1)
- [ ] `TrialsAgent` (from notebook Agent 3)
- [ ] `CrossIndicationCoordinator` + KG (from notebook Agent 4)
- [ ] `ReportSynthesizerAgent` (from notebook Agent 5)
- [ ] LangGraph workflow wiring
- [ ] Frontend: full report tabs

### Phase 4 — Polish & Harden (Week 4)

- [ ] Retry logic (from notebook `should_retry`)
- [ ] Source caching (avoid re-fetching same URL)
- [ ] Rate limiting on API
- [ ] Error handling + partial results (some sources fail, others succeed)
- [ ] Integration tests end-to-end
- [ ] PrimeKG optional loader
- [ ] Qdrant PDF fallback (optional)

---

## 14. Testing Strategy

### Backend

| Layer | What to test | How |
|-------|-------------|-----|
| `core/models` | Validation, serialization | Unit |
| `sources/search` | Query building, result parsing | Unit with mocked HTTP |
| `sources/fetch` | Timeout, extraction | Unit with fixture HTML |
| `agents/source_reader` | Prompt → summary | Unit with mocked LLM |
| `agents/factory` | Spawn events, parent/child tree | Unit |
| `pipeline/workflow` | Full run with all mocks | Integration |
| `api/runs` | POST + GET + SSE | Integration with TestClient |

### Frontend

| Layer | What to test | How |
|-------|-------------|-----|
| `api_client` | Request building, response parsing | Unit with mocked responses |
| `components/agent_trace` | Tree rendering from event list | Unit with fixture events |
| `state/session` | State initialization | Unit |

**Rule:** Frontend tests never start the backend. Backend tests never import Streamlit.

---

## 15. Deployment Topology

### Development

```
localhost:8501  →  Streamlit (frontend)
localhost:8000  →  Uvicorn (backend)
```

### Production (Docker Compose)

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    volumes:
      - primekg_cache:/tmp/primekg

  frontend:
    build: ./frontend
    ports: ["8501:8501"]
    environment:
      CDSS_API_URL: http://backend:8000
    depends_on: [backend]

  qdrant:          # optional
    image: qdrant/qdrant
    ports: ["6333:6333"]
```

### Future: Replace Streamlit

Because the frontend is API-only, swapping Streamlit for React/Next.js requires:
1. Implement the same `CDSSApiClient` in TypeScript
2. Build UI components equivalent to `chat`, `agent_trace`, `report_view`
3. Zero backend changes

---

## Appendix A — Makefile Targets

```makefile
.PHONY: dev dev-backend dev-frontend test lint docker-up

dev-backend:
	cd backend && uvicorn cdss.main:app --reload --port 8000

dev-frontend:
	cd frontend && streamlit run app/main.py --server.port 8501

dev:
	@echo "Run 'make dev-backend' and 'make dev-frontend' in separate terminals"

test:
	pytest tests/backend tests/frontend -v

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

## Appendix C — Frontend/Backend Import Guard

Add to `frontend/app/main.py` at startup (dev-only assertion):

```python
FORBIDDEN_PREFIXES = ("cdss", "backend", "langgraph", "openai", "qdrant_client")
import sys
for mod in sys.modules:
    for prefix in FORBIDDEN_PREFIXES:
        if mod.startswith(prefix):
            raise RuntimeError(f"Frontend must not import backend module: {mod}")
```

Add to CI:

```bash
# Ensure frontend requirements contain no backend deps
! grep -iE "langgraph|openai|qdrant|fastapi|uvicorn" frontend/requirements.txt
```

---

*Document version: 0.1.0 — 2026-06-20*
