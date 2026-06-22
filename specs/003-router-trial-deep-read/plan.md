# Implementation Plan: Router, Chat Mode, and Trial Deep-Read Pipeline

**Branch**: `003-router-trial-deep-read` | **Date**: 2026-06-22 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/003-router-trial-deep-read/spec.md`

## Summary

Add a **RouterAgent** in `cdss/agents/router/`; the UI calls `route_message()` then either `chat_reply()` or `start_run()`. Extend the LangGraph pipeline by replacing the thin `node_trials` with **`node_trials_read`**: a single **TrialsCoordinatorAgent** that searches ClinicalTrials.gov, ranks results, and fans out **TrialReader** agents (same bounded-parallel pattern as `ResearchCoordinatorAgent` → `SourceReaderAgent`). Add **TrialAggregatorAgent** alongside the existing **ResearchAggregatorAgent**; both feed the **ReportSynthesizer**.

The graph becomes:

```text
[UI] → route_message() → chat_reply() | research_subgraph

research_subgraph:
  intake → research (existing) → trials_read → cross_indication → synthesize
```

`node_trials_read` replaces `node_trials` and mirrors `node_research`: one LangGraph node that (1) spawns **TrialsCoordinatorAgent** (search, rank, fan-out readers), then (2) spawns **TrialAggregatorAgent** on the returned summaries. No separate graph node for the aggregator.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Existing stack + `curl-cffi` (trials search already on branch)  
**Storage**: `st.session_state` gains `last_report`; pipeline state gains `trial_summaries`, `trials_matched_count`, `trials_aggregated`  
**Testing**: pytest with mocked router LLM, mocked CT.gov search + per-NCT fetch, coordinator fan-out tests, trace + chat latency smokes  
**Target Platform**: `streamlit run app/main.py` / `./run`  
**Performance Goals**: ≤ 5 concurrent trial LLM reader calls; trial search + 5 reads within existing ~60 s budget; chat path &lt; 5 s  
**Constraints**: `MAX_READERS = 5` from config; `cdss/` MUST NOT import streamlit; pipeline spawns via factory; router/chat in `cdss/` only  
**Scale/Scope**: 4 new pipeline agent types + router/chat modules; 1 replaced LangGraph node; UI wiring in `app/main.py` only

## Constitution Check

| Principle | How this plan complies |
|-----------|------------------------|
| **I. Deep Modules** | Router, Chat, TrialsCoordinator, TrialReader, TrialAggregator as separate ≤200-line modules |
| **II. UI/Core Separation** | Router + ChatAgent live in `cdss/agents/`; UI calls narrow `route_message()` / `chat_reply()` — no LLM logic in `app/` |
| **III. Free-Model-First** | Router uses same Groq client with low `max_tokens` (≤256) |
| **IV. Factory + Events** | Coordinator spawns readers via factory; new `TRIALS_COORDINATOR`, `TRIAL_READER`, `TRIAL_AGGREGATOR` |
| **V. Research-Only Safety** | Chat agent includes disclaimer; trial readers summarize, never prescribe |
| **VI. Surgical Changes** | Replace `node_trials`; extend `_parse()` for keywords; do not rewrite intake |

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
│   ├── chat/
│   │   └── chat_agent.py            # NEW — educational replies (no external APIs)
│   └── trials/
│       ├── trials_agent.py            # DEPRECATE — logic moves to coordinator
│       ├── coordinator_agent.py       # NEW — search, rank, fan-out readers
│       ├── trial_reader_agent.py      # NEW — per-NCT deep read + LLM summary
│       └── aggregator_agent.py        # NEW — merge trial summaries
├── integrations/
│   └── clinical_trials.py           # DONE: fetch_trials+curl_cffi; ADD fetch_study, rank_trials, keywords in _parse
├── config/
│   ├── sources.yaml                 # trials.max_readers, max_search_results
│   └── registry.py                  # parse trials config block
├── pipeline/
│   ├── workflow.py                  # replace trials edge with trials_read node
│   ├── nodes.py                     # node_trials_read: coordinator → aggregator (like node_research)
│   └── state.py                     # trial_summaries, trials_matched_count, trials_aggregated
app/
├── main.py                          # route before _submit_message; chat_reply branch
└── chat_bridge.py                   # sync wrappers: route_and_reply() via asyncio.run()

tests/
├── core/unit/agents/test_router.py
├── core/unit/agents/test_trials_coordinator.py
├── core/unit/integrations/test_clinical_trials_rank.py
├── core/integration/test_trials_read_pipeline.py   # FR-002, SC-002, SC-003
└── app/unit/test_chat_latency.py                 # SC-001 smoke
```

## Phase 0: Research (see research.md)

- Router schema and prompt design
- Trial ranking on `ClinicalTrial` metadata (title, status, phase, keywords)
- Reuse `SourceReader` pattern vs new `TrialReader` (separate — different fetch path)

## Phase 1: Design (see data-model.md, contracts/)

- `RouteDecision`, `TrialSummary`, extend `ClinicalTrial.keywords`, extend `PipelineState`
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
| Ranking without keywords | Extend `_parse()` to populate `ClinicalTrial.keywords` from `conditionsModule` |
