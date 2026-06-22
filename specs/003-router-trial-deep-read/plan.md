# Implementation Plan: Router, Chat Mode, and Trial Deep-Read Pipeline

**Branch**: `003-router-trial-deep-read` | **Date**: 2026-06-22 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/003-router-trial-deep-read/spec.md`

## Summary

Add a **RouterAgent** at the Streamlit submission boundary to branch between lightweight **chat** and full **research** paths. Extend the LangGraph pipeline with a **TrialsCoordinator** that searches ClinicalTrials.gov, ranks results, and fans out **TrialReader** agents (same bounded-parallel pattern as `ResearchCoordinatorAgent` → `SourceReaderAgent`). Introduce **TrialAggregator** (or generalize `ResearchAggregatorAgent` into a shared **DocumentAggregator**) before the existing **ReportSynthesizer**.

The graph becomes:

```text
[UI] → Router → chat_response | research_subgraph

research_subgraph:
  intake → research (existing) → trials_search → trials_read → cross_indication → synthesize
```

`trials_search` replaces the thin `TrialsAgent` one-shot API call. `trials_read` is new coordinator + N readers.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Existing stack + `curl-cffi` (already added for trials search)  
**Storage**: `st.session_state` gains `last_report`, `chat_mode` history; pipeline state gains `trial_summaries`, `trials_matched_count`  
**Testing**: pytest with mocked router LLM, mocked CT.gov search + per-NCT fetch, coordinator fan-out tests  
**Target Platform**: `streamlit run app/main.py` / `./run`  
**Performance Goals**: ≤ 5 concurrent LLM reader calls; trial search + 5 reads within existing ~60 s budget  
**Constraints**: `MAX_READERS = 5` from config; `cdss/` MUST NOT import streamlit; all spawns via factory  
**Scale/Scope**: 3 new agent types, 2 new LangGraph nodes, router in `app/` or `cdss/agents/router/`

## Constitution Check

| Principle | How this plan complies |
|-----------|------------------------|
| **I. Deep Modules** | Router, TrialsCoordinator, TrialReader, TrialAggregator as separate ≤200-line modules |
| **II. UI/Core Separation** | Router can live in `cdss/agents/router/`; UI calls `route_message()` then `start_run()` or `chat_reply()` |
| **III. Free-Model-First** | Router uses same Groq client with low `max_tokens` (≤256) |
| **IV. Factory + Events** | Coordinator spawns readers via factory; new `AgentType.TRIAL_READER`, `TRIALS_COORDINATOR` |
| **V. Research-Only Safety** | Chat agent includes disclaimer; trial readers summarize, never prescribe |
| **VI. Surgical Changes** | Extend workflow edges; do not rewrite intake/synthesizer |

**Result**: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/003-router-trial-deep-read/
├── spec.md
├── context.md
├── plan.md              # This file
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── router.md
│   └── trials-read.md
└── tasks.md
```

### Source Code (new / changed)

```text
cdss/
├── agents/
│   ├── router/
│   │   └── router_agent.py          # NEW — classify chat | research | clarify
│   └── trials/
│       ├── trials_agent.py            # DEPRECATE or slim to search-only helper
│       ├── coordinator_agent.py       # NEW — search, rank, fan-out readers
│       ├── trial_reader_agent.py      # NEW — per-NCT deep read + LLM summary
│       └── aggregator_agent.py        # NEW — merge trial summaries
├── integrations/
│   └── clinical_trials.py           # ADD fetch_study(nct_id), rank_trials()
├── pipeline/
│   ├── workflow.py                  # ADD trials_read node; optional router outside graph
│   ├── nodes.py                     # node_trials_read, wire validation_flags
│   └── state.py                     # trial_summaries, trials_matched_count
├── config/
│   └── sources.yaml                 # trials.max_readers: 5, trials.max_search: 10
app/
├── main.py                          # route before _submit_message
└── components/
    └── chat_agent.py                # NEW — lightweight chat replies

tests/
├── core/unit/agents/test_router.py
├── core/unit/agents/test_trials_coordinator.py
└── core/unit/integrations/test_clinical_trials_rank.py
```

## Phase 0: Research (see research.md)

- Router schema and prompt design
- Trial ranking heuristics (recruiting &gt; active-not-recruiting; phase; title/biomarker match)
- Reuse `SourceReader` pattern vs new `TrialReader` (recommend separate — different fetch path)

## Phase 1: Design (see data-model.md, contracts/)

- `RouteDecision`, `TrialSummary`, extend `PipelineState`
- Contract for `route_message(text) -> RouteDecision`
- Contract for coordinator fan-out semantics

## Phase 2: Implementation tasks (see tasks.md)

Ordered by user story priority.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Router misclassifies patient case as chat | Default ambiguous → `clarify`; example pills always force `research` |
| 5 LLM reads blow rate limits | Semaphore + token budget in reader prompt; rank best trials first |
| Eligibility text too long for LLM | Truncate to `max_content_chars` with head+tail or section extract |
| CT.gov 403 on per-study fetch | Same `curl_cffi` client as search |
