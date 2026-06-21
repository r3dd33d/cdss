# Feature Specification: CDSS Multi-Agent Clinical Research Pipeline

**Feature Branch**: `001-cdss-multi-agent-pipeline`  
**Created**: 2026-06-21  
**Status**: Draft  
**Input**: Port `CDSS_Pipeline_Colab.ipynb` (5-agent research pipeline) into a production-grade, deep-module system: a single Streamlit application that runs an AgentFactory + LangGraph pipeline in-process on a free Groq model, with a live in-app agent trace. (Refined to align with Constitution v2.0.0 — Streamlit-only, no separate web backend.)

## Overview

A patient (or caregiver) describes a diagnosis in plain language — or uploads a
test-result PDF — and receives a plain-English **research report**: standard-of-care
options from medical guidelines, matching active clinical trials, and off-label
therapy hypotheses surfaced from a biomedical knowledge graph. While the system
works, the user watches a **live tree of agents** spawning and completing.

This is a research and education tool. It is **not medical advice** and says so on
every surface.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get a research report from a free-text description (Priority: P1) 🎯 MVP

A user types "I'm a 54-year-old with stage III NSCLC, EGFR exon 19 deletion, on
osimertinib, no prior chemo." The system parses the profile, gathers
standard-of-care guidance from trusted guideline sites, and returns a structured
report with a profile summary, standard-care summary, cited sources, and the
mandatory disclaimer.

**Why this priority**: This is the core value loop and a complete MVP on its own —
intake + research + report is useful even before trials and off-label discovery
exist. Everything else layers on top.

**Independent Test**: Submit a free-text message to start a run, read the run to
completion, and verify the report contains a parsed condition/stage, a
standard-care summary, at least one cited source, and the disclaimer — with all
external calls mocked.

**Acceptance Scenarios**:

1. **Given** a valid free-text description, **When** the user submits it, **Then** the system returns a run identifier immediately and the run reaches completed with a report whose profile matches the stated condition and stage.
2. **Given** a completed run, **When** the report is rendered, **Then** every source claim links to a source URL and the medical disclaimer is present.
3. **Given** an empty or over-length message, **When** the user submits it, **Then** the system rejects it with a validation error and no run is created.

---

### User Story 2 - Watch agents work in a live trace (Priority: P1)

As the pipeline runs, the user sees agents appear in a tree: Intake, then a
Research Coordinator that spawns one Source-Reader per discovered URL in parallel,
then an Aggregator — each node showing status (running / done / failed) and
duration. A source that times out shows as failed without breaking the run.

**Why this priority**: Live tracing is the headline differentiator over the
notebook and the reason for the event-driven core. It is independently
demonstrable against any run.

**Independent Test**: Drive a run with mocked sources (one of which fails) and
consume the in-process event stream; assert it contains a parent→child spawn tree
with spawned / completed / failed events and a terminal run-completed event.

**Acceptance Scenarios**:

1. **Given** a running pipeline, **When** the coordinator discovers N URLs, **Then** N Source-Reader spawn events appear as children of the coordinator and resolve in parallel.
2. **Given** one source fetch times out, **When** the run continues, **Then** that reader is marked failed, other readers still complete, and the run finishes with partial results.
3. **Given** the UI is consuming the run's event stream, **When** the run completes, **Then** it receives a single terminal run-completed event and the stream ends.

---

### User Story 3 - Clinical trial matching (Priority: P2)

After research, the system queries ClinicalTrials.gov for active/recruiting trials
matching the patient's condition and biomarkers and includes a trials section
(NCT id, title, phase, status, locations, eligibility summary, link) in the report.

**Why this priority**: High patient value, but depends on a parsed profile (US1)
and is additive to the report rather than required for an MVP.

**Independent Test**: With a parsed profile and a mocked ClinicalTrials.gov v2
response, verify the report's trials section is populated with normalized trial
records and a count.

**Acceptance Scenarios**:

1. **Given** a parsed condition and biomarker, **When** the trials agent runs, **Then** the report includes ≥0 normalized trials and a `trials_count`, each with a valid NCT link.
2. **Given** ClinicalTrials.gov is unreachable, **When** the trials agent runs, **Then** it emits a failure event and the run still completes with an empty trials section.

---

### User Story 4 - Off-label cross-indication discovery (Priority: P2)

The system traverses the PrimeKG biomedical knowledge graph from the patient's
gene/biomarker to find drugs approved for other indications that share a pathway,
and presents them as clearly-labeled, evidence-graded **hypotheses to discuss with
a doctor** — never recommendations.

**Why this priority**: Differentiating but optional: it requires the (large) PrimeKG
load and gracefully degrades. The pipeline must run fully without it.

**Independent Test**: With a stub knowledge graph containing a known gene→pathway→drug
path, verify the cross-indication agent returns evidence-labeled hypotheses; with the
graph unavailable, verify the phase is skipped and the run still completes.

**Acceptance Scenarios**:

1. **Given** PrimeKG is loaded and the profile has a gene, **When** cross-indication runs, **Then** the report lists off-label hypotheses each with an evidence level/label and a shared-mechanism note.
2. **Given** PrimeKG fails to load, **When** the pipeline runs, **Then** the cross-indication phase is skipped, an event records the skip, and all other sections are produced.

---

### User Story 5 - PDF test-result upload (Priority: P3)

Instead of typing, the user uploads a PDF medical report; the system extracts its
text and feeds it into the same intake → report flow.

**Why this priority**: Convenience that reuses the entire pipeline; lowest priority
because free-text intake already covers the core journey.

**Independent Test**: Upload a fixture PDF, verify text extraction feeds intake, and
the resulting profile matches the document — distinct from the free-text path.

**Acceptance Scenarios**:

1. **Given** a readable PDF, **When** the user uploads it, **Then** the run produces a report whose profile reflects the PDF contents.
2. **Given** an unreadable/empty PDF, **When** uploaded, **Then** the system returns a clear validation error.

### Edge Cases

- **Vague or non-clinical input**: intake produces an empty/low-confidence profile → the run completes with a clarifying note rather than fabricated fields.
- **All sources fail**: research yields no summaries → report states no guideline sources were retrieved; the run still completes (not errored).
- **LLM returns malformed JSON or markdown-fenced JSON**: parsing strips fences and, on failure, the agent emits a validation flag and the retry rule (max 2) applies.
- **Slow/stuck source**: per-fetch timeout caps wait; the reader fails fast and the run is not blocked.
- **UI interrupted mid-run** (Streamlit rerun/refresh): the UI can re-read the run's current status and final report from the in-progress run without restarting it.
- **Prompt-injection text inside a fetched page** ("ignore previous instructions…"): treated as untrusted content; the source-reader summarizes only patient-relevant facts and never executes embedded instructions.
- **Disclaimer missing**: a report without the disclaimer is a defect and must fail a quality gate.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a research request containing either free text or an uploaded PDF and start the run without blocking the UI, returning a run identifier the UI can track immediately.
- **FR-002**: System MUST parse the input into a structured patient profile (condition, stage, biomarkers, current medications, prior therapies) without inventing values not supported by the input.
- **FR-003**: System MUST retrieve standard-of-care information by searching a configurable allowlist of trusted guideline sites and reading discovered sources, summarizing only patient-relevant content with citations.
- **FR-004**: System MUST run one isolated Source-Reader unit per discovered source, in parallel, bounded by a configured maximum, and tolerate individual source failures without failing the run.
- **FR-005**: System MUST query ClinicalTrials.gov (v2) for matching active/recruiting trials and include normalized trial records in the report.
- **FR-006**: System MUST, when the knowledge graph is available, surface off-label drug hypotheses via gene→pathway→drug traversal, each labeled as a hypothesis with an evidence level; and MUST skip this phase gracefully when the graph is unavailable.
- **FR-007**: System MUST synthesize a single plain-English markdown report combining profile, standard care, trials, and off-label sections, and MUST include the medical disclaimer in every report.
- **FR-008**: System MUST create every agent through a single factory that assigns a run id and parent id, and MUST emit typed lifecycle events (spawned, started, source discovered/fetched, LLM call, completed, failed) plus run/phase events for each run.
- **FR-009**: System MUST publish agent lifecycle events to a live per-run event stream that the UI consumes in-process, ending with a terminal run-completed (or run-failed) event.
- **FR-010**: System MUST allow the UI to read a run's current status and, once complete, retrieve the final structured report.
- **FR-011**: System MUST apply a retry rule when synthesis produces critical validation errors, bounded to a maximum of 2 retries (preserving notebook behavior).
- **FR-012**: System MUST select the LLM at runtime from available free-tier (Groq) models by a configured preference order (DeepSeek R1 distill first, Llama fallback), with no hard-coded model id.
- **FR-013**: The UI layer MUST contain no agent, LLM, prompt, or external-call logic and MUST NOT hold secrets; all such logic lives in a headless core that the UI invokes through one narrow runner interface, and the core MUST NOT import the UI framework. A build-time guard MUST enforce this separation.
- **FR-014**: System MUST validate and sanitize all inbound input (empty/over-length text, malformed PDF) at the entry point and never expose secrets in outputs, logs, or events.
- **FR-015**: System MUST treat fetched web/PDF content as untrusted and resistant to prompt injection; agents MUST NOT act on instructions embedded in sources.
- **FR-016**: Source sites, search provider, fetch limits, model preference, and token budgets MUST be configurable via YAML without code changes.
- **FR-017**: The UI MUST display the medical disclaimer persistently and render the live agent trace and the final report sections.

### Key Entities *(include if feature involves data)*

- **PatientProfile**: condition, stage, biomarkers (gene, variant type, details), current medications, prior therapies. Derived from intake.
- **SourceRef / SourceSummary**: a discovered source (url, title, site id, rank) and its patient-scoped summary (relevant excerpt, confidence, fetch duration, owning agent run id).
- **ClinicalTrial**: nct id, title, phase, status, locations, eligibility summary, url.
- **OffLabelHypothesis**: drug name, approved indication, shared mechanism, evidence level (1–4), evidence label, citation.
- **Run**: a single pipeline execution (run id, status, phase, timestamps, validation flags, final report).
- **AgentEvent**: a typed observability record (event type, agent type, run id, parent run id, label, timing, payload) used to build the live trace tree.
- **FinalReport**: markdown report plus structured profile, sources, trials count, hypotheses count.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a typical free-text request, the user receives a complete report (profile + standard care + sources + disclaimer) within ~60 seconds on the free model tier.
- **SC-002**: 100% of produced reports contain the medical disclaimer and at least one cited source for every non-empty standard-care claim.
- **SC-003**: The Research Coordinator reads up to the configured maximum of sources concurrently; a single failed/timed-out source never aborts a run (≥1 failing source in a batch still yields a completed run with partial results).
- **SC-004**: The UI renders the agent trace purely from the core's event stream and contains no agent/LLM logic, and the headless core imports no UI framework — verified by the import guard and a passing CI check.
- **SC-005**: Swapping the LLM model or provider, or toggling a source site, requires only configuration changes (no edits to agent code) — demonstrated by changing `sources.yaml`.
- **SC-006**: No core source file exceeds the constitutional file-size limit, and every ported notebook agent has a corresponding focused module and unit test.
- **SC-007**: With PrimeKG unavailable, the pipeline still completes and produces all non-off-label sections (graceful degradation).

## Assumptions

- Groq free-tier access with a valid `GROQ_API_KEY` is available to the app environment; model availability is queried at runtime.
- A search provider key (e.g., Serper/Tavily) is available; the allowlist of guideline sites is curated in config.
- "trimlet" in the request refers to **Streamlit** — the single application that runs the agent pipeline in-process and visualizes it; there is no separate web/API server in v1 (per Constitution v2.0.0).
- The system is single-tenant / local-first for v1 (no multi-user auth); persistence of runs beyond process memory is optional for v1.
- PrimeKG (Harvard Dataverse) and Qdrant are optional dependencies; their absence degrades gracefully and does not block the core loop.
- This release ports the notebook's observable behavior; clinical accuracy review and regulatory compliance are out of scope and explicitly disclaimed.
