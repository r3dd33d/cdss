# Data Model: Router, Chat Mode, and Trial Deep-Read

## New / Extended Entities

### RouteDecision

| Field | Type | Description |
|-------|------|-------------|
| `mode` | `"chat" \| "research" \| "clarify"` | Routing outcome |
| `confidence` | `float` | 0–1 classifier confidence |
| `clarifying_question` | `str` | Populated when `mode == clarify` |

### ClinicalTrial (extended)

| Field | Type | Description |
|-------|------|-------------|
| `keywords` | `list[str]` | From `conditionsModule.keywords` at search-parse time; used by `rank_trials()` |

All existing fields (`nct_id`, `title`, `phase`, `status`, `locations`, `eligibility_summary`, `url`) unchanged.

### TrialSummary (new)

Reader output after per-NCT deep fetch.

| Field | Type | Description |
|-------|------|-------------|
| `nct_id` | `str` | NCT identifier |
| `title` | `str` | Brief title |
| `phase` | `str` | Trial phase |
| `status` | `str` | Recruiting status |
| `url` | `str` | clinicaltrials.gov link |
| `relevant_excerpt` | `str` | LLM summary: fit, eligibility highlights, interventions |
| `patient_fit_notes` | `str` | Explicit match/mismatch vs profile |
| `confidence` | `float` | Reader confidence heuristic |
| `agent_run_id` | `str` | Trace linkage |

### PipelineState (extensions)

| Field | Type | Set by |
|-------|------|--------|
| `clinical_trials` | `list[ClinicalTrial]` | trials search (all matched metadata) |
| `trials_matched_count` | `int` | trials coordinator after search |
| `trial_summaries` | `list[TrialSummary]` | trials_read phase |
| `trials_aggregated` | `str` | TrialAggregator |
| `route_mode` | `str` | Router (optional, for trace) |

### Session state (UI)

| Key | Type | Purpose |
|-----|------|---------|
| `last_report` | `FinalReport \| None` | Chat follow-ups |
| `messages` | `list` | Unchanged |

## Agent Type Enum (additions)

```text
TRIALS_COORDINATOR   # pipeline — replaces thin TRIALS node
TRIAL_READER
TRIAL_AGGREGATOR
```

**Pre-pipeline (not factory-spawned):** `RouterAgent`, `ChatAgent` in `cdss/agents/router/` and `cdss/agents/chat/`. Invoked via `route_message()` / `chat_reply()` before `Runner.run()`. FR-007 applies to LangGraph pipeline agents only.

`TRIALS` enum value deprecated when coordinator lands.

## Aggregators (v1)

| Agent | Input | Output field |
|-------|-------|--------------|
| `ResearchAggregatorAgent` (existing) | `list[SourceSummary]` | `standard_care_summary` |
| `TrialAggregatorAgent` (new) | `list[TrialSummary]` | `trials_aggregated` |

Unified `DocumentAggregator` deferred to v2 (see spec non-goals).

## Event Trace Shape

```text
RUN_STARTED
  └─ INTAKE
  └─ RESEARCH_COORDINATOR
       └─ SOURCE_READER × min(sources, 5)
  └─ RESEARCH_AGGREGATOR
  └─ TRIALS_COORDINATOR
       └─ TRIAL_READER × min(ranked_trials, 5)
  └─ TRIAL_AGGREGATOR
  └─ CROSS_INDICATION_COORD
  └─ REPORT_SYNTHESIZER
RUN_COMPLETED
```

Pre-pipeline (optional UI-level events, not factory children):

```text
ROUTE_DECIDED → chat | research | clarify
CHAT_REPLIED   (chat mode only)
```

## Config (`sources.yaml` additions)

```yaml
trials:
  max_search_results: 10
  max_readers: 5
  rank_recruiting_boost: 2
```

Loaded via `SourceRegistry.trials` (see task T008b).
