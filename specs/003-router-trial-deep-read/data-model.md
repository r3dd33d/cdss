# Data Model: Router, Chat Mode, and Trial Deep-Read

## New / Extended Entities

### RouteDecision

| Field | Type | Description |
|-------|------|-------------|
| `mode` | `"chat" \| "research" \| "clarify"` | Routing outcome |
| `confidence` | `float` | 0–1 classifier confidence |
| `clarifying_question` | `str` | Populated when `mode == clarify` |

### TrialSummary (new)

Extends trial metadata with reader output.

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
| `clinical_trials` | `list[ClinicalTrial]` | trials search (metadata, all matched) |
| `trials_matched_count` | `int` | trials search |
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
ROUTER           # pre-pipeline (may run in app layer)
TRIALS_COORDINATOR
TRIAL_READER
TRIAL_AGGREGATOR
```

`TRIALS` may remain as thin search wrapper or merge into coordinator.

## Event Trace Shape

```text
RUN_STARTED
  └─ INTAKE
  └─ RESEARCH_COORDINATOR
       └─ SOURCE_READER × N
  └─ RESEARCH_AGGREGATOR
  └─ TRIALS_COORDINATOR
       └─ TRIAL_READER × min(matched, 5)
  └─ TRIAL_AGGREGATOR
  └─ CROSS_INDICATION_COORD
  └─ REPORT_SYNTHESIZER
RUN_COMPLETED
```

## Config (`sources.yaml` additions)

```yaml
trials:
  max_search_results: 10
  max_readers: 5
  rank_recruiting_boost: 2
```
