# Phase 0 — Research & Decisions

Decisions that de-risk the plan before design. Each is a resolved
`Decision / Rationale / Alternatives` triplet grounded in the notebook + constitution.

## R1. LLM runtime & model selection (free tier)

- **Decision**: Use **Groq** via the OpenAI-compatible endpoint
  (`base_url=https://api.groq.com/openai/v1`). At startup, list available models and
  pick the first match from a YAML preference order: `deepseek-r1-distill-llama-70b` →
  `…-qwen-32b` → `…-llama-8b` → `llama-3.3-70b-versatile` → … → `llama-3.1-8b-instant`.
  Expose a single `chat(prompt, max_tokens)` and a `strip_json_fences()` helper.
- **Rationale**: Mirrors notebook Cell 8 exactly; keeps us on a free tier; never
  hard-codes a model (Constitution III). Runtime discovery survives Groq deprecating models.
- **Alternatives**: Pin one model (rejected — breaks when Groq retires it); NVIDIA NIM
  free tier (viable later, hidden behind the same `LLMClient` interface).

## R2. Search provider for standard-of-care

- **Decision**: Pluggable `AbstractSearchProvider` with **Serper** as default and
  **Tavily**/Google CSE as config-selectable. Queries are **site-scoped** to a curated
  allowlist (`nccn.org`, `esmo.org`, `cancer.gov`, `nice.org.uk`, …) via `site:` filters,
  `top_k_per_site` and `max_total_sources` from config.
- **Rationale**: The notebook's Standard-Care agent used Qdrant RAG over uploaded PDFs;
  the production design replaces it with live, citable guideline search (one source → one
  reader agent), which is more trustworthy and trace-able. Config-over-code (Constitution).
- **Alternatives**: Keep Qdrant-only RAG (rejected as primary — needs pre-loaded corpus);
  unrestricted web search (rejected — low trust, injection risk). Qdrant retained as an
  optional fallback for user-uploaded PDFs only.

## R3. Live trace delivery: in-process event stream (no SSE)

- **Decision**: **In-process delivery** — the core `EventBus` feeds a thread-safe queue
  that the Streamlit UI drains each fragment tick via `runner_bridge.drain_events()`,
  terminated by `RUN_COMPLETED`/`RUN_FAILED`. No HTTP/SSE/WebSocket; the UI re-reads the
  in-progress run on a Streamlit rerun/refresh.
- **Rationale**: Constitution II makes this a single Streamlit app with no web server, so
  events stay in-process; this is simpler and lower-latency than a transport layer and
  needs no `sse-starlette`/uvicorn.
- **Alternatives**: SSE/WebSocket (rejected — require a server we no longer have); polling
  a status object only (rejected — no live tree).

## R4. Event model & per-run bus

- **Decision**: In-process **pub/sub `EventBus` keyed by `run_id`** plus an append-only
  `TraceStore` per run. `AgentFactory.spawn()` is the sole emitter of spawn/lifecycle
  events; `app/runner_bridge.py` drains them onto a thread-safe queue the UI reads.
- **Rationale**: Single-tenant/local-first v1 needs no broker; keeps the spawn→event
  invariant in one place (Constitution IV). Swappable for Redis pub/sub later behind the
  same interface.
- **Alternatives**: Redis/Kafka (rejected as premature for v1 scale); logging-only
  (rejected — can't build a live tree).

## R5. PrimeKG load & graceful degradation

- **Decision**: Load PrimeKG nodes/edges from **Harvard Dataverse** into a NetworkX
  `MultiDiGraph`, cached at `PRIMEKG_CACHE_DIR`. Loading is **lazy and optional**: a
  `KG_AVAILABLE` flag gates the cross-indication phase; failure emits a skip event and the
  run proceeds (FR-006, SC-007). Traversal = BFS gene→pathway→drug (notebook Cell 16).
- **Rationale**: PrimeKG is large and slow; the core loop must not depend on it. Matches
  notebook Cell 14's try/except degradation.
- **Alternatives**: Neo4j (rejected for v1 — extra service; revisit for scale); bundle a
  subgraph (possible optimization later).

## R6. Concurrency & free-tier rate limits

- **Decision**: Source-Readers run via `asyncio.gather` bounded by `max_total_sources`
  (default 5) and a semaphore; per-fetch timeout (default 15 s). LLM calls respect token
  budgets per agent from config. Failures are isolated (partial results allowed).
- **Rationale**: Honors SC-003 (one failing source never aborts a run) and free-tier
  throughput limits without code changes (Constitution III/VII).
- **Alternatives**: Unbounded parallelism (rejected — rate-limit/timeout storms).

## R7. Streamlit non-blocking run + fragment refresh ("trimlet")

- **Decision**: `runner_bridge.start_run()` runs the async core pipeline on a **background
  thread** and returns a `RunHandle`; the UI stores `run_id` in `st.session_state` and an
  `@st.fragment(run_every="0.7s")` drains events into the trace and `st.rerun()`s on
  `done()`, then renders the report. The background thread runs only core code — it has no
  `ScriptRunContext`, so it never calls `st.*`.
- **Rationale**: Keeps Streamlit a pure view over core events (Constitution II); no
  agent/LLM logic in the UI. Confirms "trimlet" = Streamlit as the in-process run driver.
- **Alternatives**: Blocking the script on the run (rejected — freezes the UI, no live
  tree); embedding agents in the UI (rejected — violates UI/core separation).

## R8. Notebook → module mapping (deep-module decomposition)

- **Decision**: Decompose monolithic cells into leaf modules: Cell 6 state →
  `core/models/*` + `pipeline/state.py`; Cell 8 LLM → `llm/client.py` + `model_selector.py`
  + `json_utils.py`; Cells 14/16 KG → `knowledge/graph/{loader,queries}.py`; Cell 22 trials
  → `integrations/clinical_trials.py`; each `agent_*` (Cells 18–26) → its own module under
  `agents/`; Cell 28 graph → `pipeline/workflow.py`; Cells 30–34 run → `pipeline/runner.py`
  (core) + `app/runner_bridge.py` (UI driver).
- **Rationale**: Directly satisfies Constitution I (no large files) and SC-006.
- **Alternatives**: One module per concern but large files (rejected — violates size gate).

## Open questions (non-blocking)

- Exact biomarker→trial query mapping for ClinicalTrials.gov v2 (refine in US3 task).
- Confidence heuristic for `SourceSummary.confidence` (start simple: presence + length).
- Whether to persist runs across restarts (deferred; in-memory for v1).
