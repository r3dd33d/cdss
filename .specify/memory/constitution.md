# CDSS Constitution

Clinical Decision Support System — a research-only, multi-agent patient-research
tool ported from `CDSS_Pipeline_Colab.ipynb` into a production-grade,
deep-module **Streamlit application** driven by a free LLM (Groq). There is no
separate web backend — Streamlit runs the agent pipeline in-process.

## Core Principles

### I. Deep Modules, Small Files (NON-NEGOTIABLE)

Every module exposes a **narrow interface over substantial functionality**
(Ousterhout's deep-module principle). Implementation complexity is hidden behind
small public surfaces.

- A single source file SHOULD stay under ~200 lines and MUST stay under 400.
  When a file grows past this, split by responsibility, not by line count.
- Public interfaces are minimal: callers depend on abstract base classes and
  Pydantic models, never on concrete adapters or transport details.
- No "god" files. `agents/`, `sources/`, `knowledge/`, and `pipeline/` are
  packages of focused leaf modules, each doing one thing.
- Shallow pass-through wrappers and "manager/util/helper" grab-bags are
  prohibited unless they genuinely hide complexity.

### II. UI/Core Separation — Streamlit-Only (NON-NEGOTIABLE)

This project ships as a single Streamlit app. We do **not** use FastAPI or any
separate web server; Streamlit runs the agent pipeline in-process.

- All agent, LLM, pipeline, and adapter logic lives in a headless, importable
  core package (`cdss/`) that MUST NOT import `streamlit`.
- All UI lives in `app/`; UI modules MUST NOT contain agent, LLM, or prompt
  logic — they call the core through one narrow runner/service interface.
- Live updates flow from the core's in-memory event bus to the UI via session
  state and reruns (no HTTP/SSE server).
- A CI guard enforces that `cdss/` never imports `streamlit`, keeping the core
  testable and UI-swappable (a different UI or an API could be added later
  without touching the core).

### III. Free-Model-First & Provider Abstraction

The system runs on a **free LLM tier** (Groq) by default and never hard-codes a
model.

- Model selection is data-driven: query available models at runtime and pick by
  a configured preference order (DeepSeek R1 distill → Llama fallback), exactly
  as the notebook does.
- All LLM access goes through a single `llm/client.py` behind a narrow `chat()`
  interface. Swapping providers (or self-hosting) MUST NOT touch agent code.
- Token budgets, model preference, and limits live in YAML config, not in code.

### IV. Agents Spawn Through the Factory; Everything Emits Events

- All agent creation flows through one `AgentFactory.spawn()` — the single place
  for lifecycle, run-id generation, and parent/child tracing.
- Coordinators plan and delegate; leaf agents do exactly one unit of work
  (one source → one summary). One source = one agent.
- Adapters are not agents: HTTP fetch, search, PDF/HTML extraction, and KG
  queries live in infrastructure packages (`sources/`, `knowledge/`,
  `integrations/`), never inside agent classes.
- Every spawn, fetch, LLM call, phase transition, and failure emits a typed
  event on the per-run event bus so the UI can render a live trace tree.

### V. Research-Only Safety (NON-NEGOTIABLE)

This tool is for research and education — **not** medical advice.

- Every report and every UI surface MUST display the medical disclaimer.
- Agents MUST NOT invent doses, recommendations, or eligibility decisions; they
  summarize sourced material and flag uncertainty.
- Inputs are treated as untrusted: validate and sanitize at the API boundary;
  guard against prompt injection in fetched web content; never echo secrets.
- Patient input is sensitive. Do not log raw patient text at INFO; redact PII in
  traces and persisted events.

### VI. Surgical Changes — Minimal Diffs (NON-NEGOTIABLE)

Change only what must change; prefer the smallest edit that does the job.

- Touch a block only when necessary. If editing, adding, or removing a few lines
  achieves the goal, do that instead of deleting or rewriting the whole block.
- Preserve surrounding code, names, and structure; avoid incidental reformatting
  or churn that hides the real change in review.
- A larger rewrite is allowed only when a smaller edit cannot work, and must be
  justified in the change description.

### VII. Short Comments

Comments are brief. A comment MUST be one or two sentences — never more.

- Comment *why*, not *what*; let the code say what it does.
- No long block/banner comments, no commented-out code, no narrating obvious
  steps.

## Additional Constraints

**Technology stack** (locked unless amended): Python 3.11+, a single **Streamlit**
app (no FastAPI/Uvicorn), LangGraph orchestration, Pydantic v2 models, Groq
(OpenAI-compatible) LLM, NetworkX + PrimeKG knowledge graph, optional Qdrant
vector store, ClinicalTrials.gov API v2. Configuration via `pydantic-settings` +
YAML. The headless core (`cdss/`) and the UI (`app/`) are separate packages; the
core never imports Streamlit.

**Secrets** live only in backend environment variables (`GROQ_API_KEY`,
`SERPER_API_KEY`, …). They never appear in the frontend, in logs, in events, or
in committed files. `.env` is git-ignored; `.env.example` is the contract.

**Config over code**: allowed source sites, search provider, fetch limits, model
preference, and token budgets live in `sources.yaml` and are toggleable without
code changes.

## Development Workflow

- **Spec-driven**: changes flow constitution → spec → plan → tasks → implement.
  No production code is written ahead of an approved plan.
- **Layered tests**: pure `core/` models and `sources/` adapters are unit-tested
  with mocked I/O; the `AgentFactory` and event bus have unit tests for the
  spawn/event tree; the pipeline has integration tests with all external calls
  mocked. Core tests never import Streamlit; UI tests never run real agents.
- **Quality gates** (must pass to merge): file-size limit (Principle I), the
  `cdss/`-must-not-import-`streamlit` guard (Principle II), one-to-two-sentence
  comments (Principle VII), minimal-diff review (Principle VI), no secrets in the
  repo, disclaimer present in report output, and the full test suite green.
- **Deterministic ports of notebook logic**: each ported agent maps to a named
  notebook cell and preserves its observable behavior (intake parsing, retry
  rule, KG traversal, synthesizer disclaimer).

## Governance

This constitution supersedes ad-hoc practices. Core Principles marked
NON-NEGOTIABLE may not be waived; other constraints may be amended via a
documented change to this file with a version bump and rationale.

- Every plan MUST include a Constitution Check section and pass it before Phase 0
  research and again after design. Unavoidable violations go in the plan's
  Complexity Tracking table with justification, or the design is simplified.
- Amendments follow semantic versioning: **MAJOR** for removing/redefining a
  principle, **MINOR** for adding a principle or section, **PATCH** for
  clarifications.
- Runtime development guidance for agents lives alongside the feature artifacts
  in `specs/`; this file holds the durable, non-negotiable rules.

**Version**: 2.0.0 | **Ratified**: 2026-06-21 | **Last Amended**: 2026-06-21
