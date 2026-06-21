# Tasks: CDSS Multi-Agent Clinical Research Pipeline (Streamlit Chat UI)

**Input**: Design documents from `/specs/001-cdss-multi-agent-pipeline/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓
**Architecture**: Single Streamlit app — headless `cdss/` core + `app/` chat UI, in-process
event bus, **no FastAPI/REST/SSE** (Constitution v2.0.0, Principle II).
**Tests**: Included — the spec defines independent tests per story; the constitution
mandates layered tests. Test tasks precede the implementation they cover.

## Format: `[ID] [P?] [Story] Description`
- **[P]** = parallelizable (different files, no dependency)
- **[Story]** = US1..US5 (or SETUP/FOUND/POLISH)
- Deep modules (Principle I): every file stays ≤~200 lines SHOULD / ≤400 MUST; comments
  are one–two sentences (Principle VII).

## Path Conventions
Core: `cdss/…` (NEVER imports `streamlit`). UI: `app/…` (imports core via `runner_bridge`
only). Tests: `tests/core/…`, `tests/app/…`.

---

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 [SETUP] Create single-app skeleton: `cdss/` core tree (config, core, observability, llm, sources, knowledge, integrations, agents, pipeline) and `app/` (state, components) and `tests/{core,app}/`, with `__init__.py` where needed and an `app/main.py` placeholder.
- [ ] T002 [P] [SETUP] `pyproject.toml` + `requirements.txt`: streamlit, langgraph, pydantic, pydantic-settings, openai (Groq-compatible), httpx, trafilatura/readability, pypdf, networkx, pyyaml; optional qdrant-client + sentence-transformers. **No fastapi/uvicorn/sse-starlette.**
- [ ] T003 [P] [SETUP] `.env.example` (GROQ_API_KEY, SERPER_API_KEY, cache dirs), `.gitignore` (ignore `.env`), `README.md`, `Makefile` (`run: streamlit run app/main.py`; `test`; `lint`; `guards`).
- [ ] T004 [P] [SETUP] Tooling + three CI gate scripts: (a) **file-size** ≤400 lines over `cdss/**` and `app/**` (Principle I); (b) **import-direction guard** — fail if any `cdss/**/*.py` imports `streamlit` (Principle II); (c) **comment-length gate** — fail on any comment >2 sentences (Principle VII). Plus ruff + black, pytest + pytest-asyncio config.
- [ ] T005 [P] [SETUP] `Dockerfile` (single Streamlit image, entry `streamlit run app/main.py`) + `docker-compose.yml` (streamlit + optional qdrant).

**Checkpoint**: App installs; `cdss/` and `app/` import cleanly; guard scripts run.

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: No user-story work begins until this phase is complete — this is the
infrastructure to "lay correctly": domain core, config, observability event bus, LLM
client, and the AgentFactory.

- [ ] T006 [P] [FOUND] `cdss/core/enums.py` — `AgentType`, `RunStatus`, `EventType` (data-model.md).
- [ ] T007 [P] [FOUND] `cdss/core/exceptions.py` — FetchError, ExtractError, LLMError, IntakeError.
- [ ] T008 [P] [FOUND] `cdss/core/models/{patient,source,trial,hypothesis,report}.py` — one small Pydantic module per entity.
- [ ] T009 [P] [FOUND] `tests/core/unit/core/test_models.py` — validation/serialization per entity.
- [ ] T010 [FOUND] `cdss/config/settings.py` (pydantic-settings: keys, cache dirs, log level) + `cdss/config/sources.yaml` (sites allowlist, search, fetch, llm model_preference + token budgets).
- [ ] T011 [P] [FOUND] `cdss/sources/registry.py` — load + validate `sources.yaml` into typed config.
- [ ] T012 [FOUND] `cdss/observability/events.py` — `AgentEvent` base + typed subclasses + PII-redaction helper.
- [ ] T013 [FOUND] `cdss/observability/run_context.py` (run_id/parent/depth) + `cdss/observability/trace_store.py` (append-only per-run log).
- [ ] T014 [FOUND] `cdss/observability/event_bus.py` — per-`run_id` pub/sub; **thread-safe drain** so the UI thread can pull events produced by the background run thread (research.md R4/R7).
- [ ] T015 [P] [FOUND] `tests/core/unit/observability/test_event_bus.py` — publish/drain, ordering, replay, redaction, cross-thread safety.
- [ ] T016 [P] [FOUND] `cdss/llm/json_utils.py` (`strip_json_fences`) + `cdss/llm/model_selector.py` (runtime Groq model discovery by preference order — notebook Cell 8).
- [ ] T017 [FOUND] `cdss/llm/client.py` — narrow `LLMClient.chat(prompt, max_tokens)` over Groq OpenAI-compatible endpoint; no hard-coded model (Principle III).
- [ ] T018 [P] [FOUND] `tests/core/unit/llm/test_model_selector.py` — preference order + fallback with mocked model list.
- [ ] T019 [FOUND] `cdss/agents/base.py` — `BaseAgent` ABC + `AgentTask`/`AgentResult` bases (contracts/agents.md).
- [ ] T020 [FOUND] `cdss/agents/registry.py` — `AgentType → class` map (empty wiring slots).
- [ ] T021 [FOUND] `cdss/agents/factory.py` — `AgentFactory.spawn()` (run_id gen, event emission, registry instantiation, completed/failed). Sole spawn path.
- [ ] T022 [FOUND] `tests/core/unit/agents/test_factory.py` — spawn emits spawned/started/completed; failure → agent_failed; parent/child tree correct.
- [ ] T023 [FOUND] `cdss/pipeline/state.py` — `PipelineState` (data-model.md) incl. retry_count/max_retries.

**Checkpoint**: Factory + event bus + LLM client + core models exist and are tested.
Stories can now build on this foundation.

---

## Phase 3: User Story 1 — Research report via chat (Priority: P1) 🎯 MVP

**Goal**: Patient types a description in chat → intake → site-scoped research (parallel
source readers) → synthesized report with profile, standard care, sources, and the
disclaimer, rendered in an `st.chat_message`.

**Independent Test**: Start a run with mocked search/fetch/LLM, read it to completion,
and verify the report has parsed condition/stage, a standard-care summary, ≥1 cited
source, and the disclaimer.

### Core adapters & infra (cdss/)
- [ ] T024 [P] [US1] `cdss/sources/search/base.py` (`AbstractSearchProvider`) + `serper.py` + `site_scoped.py` (allowlist `site:` queries).
- [ ] T025 [P] [US1] `cdss/sources/fetch/base.py` (`AbstractFetcher`) + `httpx_fetcher.py` (timeout from config).
- [ ] T026 [P] [US1] `cdss/sources/extract/html.py` (trafilatura/readability) + `extract/pdf.py` (pypdf).
- [ ] T027 [P] [US1] `tests/core/unit/sources/` — site-scoped query building, fetch timeout, HTML/PDF extraction (fixtures, mocked HTTP).

### Agents (each its own module + test)
- [ ] T028 [P] [US1] `cdss/llm/prompts/intake.py` + `cdss/agents/intake/intake_agent.py` (notebook Agent 1 → `PatientProfile`; never invents fields).
- [ ] T029 [US1] `tests/core/unit/agents/test_intake.py` — parses condition/stage/biomarkers (mocked LLM); vague input → empty profile.
- [ ] T030 [P] [US1] `cdss/llm/prompts/source_reader.py` + `cdss/agents/research/source_reader_agent.py` (1 url → `SourceSummary`; ignores injected instructions, FR-015).
- [ ] T031 [US1] `tests/core/unit/agents/test_source_reader.py` — fetch→extract→summarize; timeout → isolated failure event.
- [ ] T032 [US1] `cdss/agents/research/coordinator_agent.py` — search → spawn N `SOURCE_READER` via factory in parallel (≤ max_total_sources, semaphore) → then aggregator.
- [ ] T033 [P] [US1] `cdss/agents/research/aggregator_agent.py` — merge summaries → `standard_care_summary`.
- [ ] T034 [P] [US1] `cdss/llm/prompts/synthesizer.py` + `cdss/agents/synthesis/report_agent.py` (notebook Agent 5 → `FinalReport`; **MUST embed disclaimer**, FR-007).
- [ ] T035 [US1] `tests/core/unit/agents/test_synthesizer.py` — report includes disclaimer + sources (gate SC-002).
- [ ] T036 [US1] Register US1 agents in `cdss/agents/registry.py`.

### Core pipeline + runner
- [ ] T037 [US1] `cdss/pipeline/nodes.py` (thin wrappers calling agents via factory) + `cdss/pipeline/workflow.py` (LangGraph: intake→research→synthesize MVP slice).
- [ ] T038 [US1] `cdss/pipeline/runner.py` — `build_runner()` + async `run(state)` driving the workflow + event bus, applying the retry rule (max 2, FR-011), returning `FinalReport` and exposing an optional report token stream.
- [ ] T039 [US1] `tests/core/integration/test_pipeline_mvp.py` — full MVP run (mocked search/fetch/LLM) asserts report shape + disclaimer + ≥1 source.

### Chat UI (app/) — calls core only via runner_bridge
- [ ] T040 [US1] `app/runner_bridge.py` — `start_run(text, files)` launches the async runner on a **background thread**, returns a handle with `drain_events()`, `done()`, `result()`/`report_stream()`. The thread runs only core code (no `st.*`). **Only** core touchpoint (FR-013).
- [ ] T041 [P] [US1] `app/state/session.py` — init `messages`, `run_id`, `events`, `run_status`, `report` + helpers.
- [ ] T042 [P] [US1] `app/components/disclaimer.py` — persistent medical-disclaimer banner (Principle V).
- [ ] T043 [P] [US1] `app/components/chat.py` — `st.chat_input` + `st.chat_message` history render.
- [ ] T044 [P] [US1] `app/components/report_view.py` — `st.tabs(Profile|Standard Care|Trials|Off-Label)` + `st.write_stream`/`st.markdown`; disclaimer caption.
- [ ] T045 [US1] `app/main.py` — page config, layout, disclaimer, chat input → `runner_bridge.start_run` → render report (non-blocking).
- [ ] T046 [P] [US1] `tests/app/unit/test_chat_flow.py` — `st.testing.AppTest` with a **stubbed runner_bridge** (canned report): disclaimer present, report tabs populated. No live agents.

**Checkpoint**: MVP works — a chat message yields a cited, disclaimed report.

---

## Phase 4: User Story 2 — Live agent trace (Priority: P1)

**Goal**: A side panel shows the spawn tree (coordinator → parallel readers, one failing)
updating live as the run executes.

**Independent Test**: Drive a run with a failing source and consume the in-process event
stream; assert a parent→child spawn tree + a failed node + a terminal run-completed event,
and that `agent_trace` renders it (incl. the failed node).

- [ ] T047 [US2] `app/components/agent_trace.py` — build parent→child tree from events; render with `st.status` (running→"running", completed→"complete", failed→"error"); show label + duration.
- [ ] T048 [US2] `app/main.py` — add the right-column trace panel and an `@st.fragment(run_every="0.7s")` that drains `runner_bridge` events into `session_state` and `st.rerun()` on `done()` (research.md R7).
- [ ] T049 [P] [US2] `tests/app/unit/test_agent_trace.py` — `AppTest` renders the tree from a fixture event list including a failed node.
- [ ] T050 [US2] `tests/core/integration/test_event_stream.py` — failing source → spawn tree + isolated failure + single terminal run-completed in the event bus (SC-003).

**Checkpoint**: P1 MVP complete — report + live trace. Demoable product.

---

## Phase 5: User Story 3 — Clinical trial matching (Priority: P2)

**Goal**: Add a trials section from ClinicalTrials.gov v2.

**Independent Test**: Parsed profile + mocked CT.gov response → report trials section + count.

- [ ] T051 [P] [US3] `cdss/integrations/clinical_trials.py` — CT.gov v2 query builder + response → `list[ClinicalTrial]` (notebook Cell 22); unreachable → empty + failure event.
- [ ] T052 [P] [US3] `tests/core/unit/integrations/test_clinical_trials.py` — mapping + error degradation.
- [ ] T053 [US3] `cdss/agents/trials/trials_agent.py` (profile → trials) + register; add `trials` node to `workflow.py` after research.
- [ ] T054 [US3] Wire Trials tab in `report_view.py`; integration assert `trials_count` + valid NCT links.

**Checkpoint**: Report includes trials; degrades gracefully if CT.gov is down.

---

## Phase 6: User Story 4 — Off-label cross-indication (Priority: P2)

**Goal**: PrimeKG gene→pathway→drug hypotheses, evidence-labeled; skip gracefully if KG absent.

**Independent Test**: Stub KG with a known path → labeled hypotheses; KG unavailable → phase
skipped, run still completes (SC-007).

- [ ] T055 [P] [US4] `cdss/knowledge/graph/loader.py` — PrimeKG (Harvard Dataverse) → NetworkX, cached, lazy, `KG_AVAILABLE` flag (notebook Cell 14).
- [ ] T056 [P] [US4] `cdss/knowledge/graph/queries.py` — `find_node_by_name`, `find_drugs_for_gene` BFS (notebook Cell 16).
- [ ] T057 [P] [US4] `tests/core/unit/knowledge/test_queries.py` — traversal on a stub graph; empty when unavailable.
- [ ] T058 [US4] `cdss/agents/cross_indication/{coordinator_agent,kg_traversal_agent}.py` (+ optional `hypothesis_agent.py`); register; add conditional `cross_indication` node (skipped when `KG_AVAILABLE` false).
- [ ] T059 [US4] `tests/core/integration/test_cross_indication.py` — hypotheses with KG; phase skipped + skip event without KG; run still completes.
- [ ] T060 [P] [US4] Wire Off-Label tab in `report_view.py` (labeled hypotheses, evidence level).

**Checkpoint**: All four report sections present; pipeline robust to missing KG.

---

## Phase 7: User Story 5 — PDF upload (Priority: P3)

**Goal**: Accept a PDF in the chat input and feed extracted text into intake.

**Independent Test**: Upload a fixture PDF → profile reflects document; unreadable PDF →
clear error surfaced in chat.

- [ ] T061 [US5] `app/components/chat.py` — enable `st.chat_input(accept_file=True, file_type=["pdf"])`; pass PDF bytes to `runner_bridge` (no parsing in the UI).
- [ ] T062 [US5] `app/runner_bridge.py` + `cdss/pipeline/runner.py` — route PDF bytes → `cdss/sources/extract/pdf.py` → intake; surface a validation error for unreadable/empty PDF (FR-014).
- [ ] T063 [US5] `tests/core/integration/test_pdf_intake.py` (fixture PDF → profile; bad PDF → error) + `tests/app/unit/test_pdf_upload.py` (AppTest: error message shown).

**Checkpoint**: Both free-text and PDF intake paths work through the same pipeline.

---

## Phase 8: Polish & Hardening

- [ ] T064 [P] [POLISH] `app/main.py` — `@st.cache_resource` to build the runner (Groq `LLMClient`, `AgentFactory`, KG loader) once per session; add a **"New case"** button that resets session state.
- [ ] T065 [P] [POLISH] `app/components/suggestions.py` (suggestion chips with example prompts before first message) + `app/components/feedback.py` (`st.feedback("thumbs")` on the report).
- [ ] T066 [P] [POLISH] Source-fetch caching within a run; structured logging with PII redaction (Principle V).
- [ ] T067 [P] [POLISH] `tests/core/integration/test_full_pipeline.py` — full 5-phase run with partial source failures → completed run with all available sections.
- [ ] T068 [P] [POLISH] Wire CI gates in Makefile/CI: file-size, import-direction (`cdss/` no `streamlit`), comment-length, disclaimer-present assertion (SC-002, SC-004, SC-006, Principles II/VII).
- [ ] T069 [P] [POLISH] Docs: `README.md` quickstart (`streamlit run app/main.py`) + `docs/AGENTS.md` (agent catalog). (`ARCHITECTURE.md` already realigned to the Streamlit-only design.)
- [ ] T070 [P] [POLISH] `tests/app/unit/test_input_validation.py` — assert empty / over-length chat text raises a chat error and starts **no** run (US1 AS3, FR-014, gap L1).
- [ ] T071 [P] [POLISH] `tests/core/integration/test_config_swap.py` — toggling a site in `sources.yaml` and reordering `model_preference` changes behavior with **no code edits** (SC-005).
- [ ] T072 [P] [POLISH] Perf smoke check (`tests/core/integration/test_latency.py`, opt-in marker): a fully-mocked end-to-end run completes well under the SC-001 budget; document the ~60 s real-tier target in `README.md`.

---

## Dependencies & Parallelization

- **Setup (T001–T005)** → **Foundational (T006–T023)** block everything. Within each, `[P]`
  tasks touch different files and can run together.
- **Story order by priority**: US1 (T024–T046) → US2 (T047–T050) = the **P1 MVP**. US3
  (T051–T054) and US4 (T055–T060) are independent P2 add-ons; US5 (T061–T063) is P3;
  Polish (T064–T069) last.
- **Critical path**: T021 (factory) → T032 (coordinator spawns readers) → T038
  (`pipeline/runner`) → T040 (`runner_bridge` bg thread) → T048 (fragment trace). Build the
  factory + thread-safe event bus first; the UI hangs off them.

## Notes
- Each `[P]` core/UI module is a small, single-responsibility file behind an ABC/Pydantic or
  component interface — the deep-module mandate (Principle I).
- The background run thread produces events only; it **never** calls `st.*` (no
  `ScriptRunContext`). The UI renders from `session_state` in the fragment.
- Tests mock LLM/HTTP/CT.gov/KG and stub `runner_bridge`; no test hits a live external
  service or the free Groq quota. Core tests never import `streamlit`; UI tests never run
  real agents.
