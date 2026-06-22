# Context: Router, Chat Mode, and Trial Deep-Read

**Feature**: 003-router-trial-deep-read  
**Depends on**: 001-cdss-multi-agent-pipeline, 002-chat-ui-layout  
**Prep commits**: trials `curl-cffi` + `fetch_trials` fix, suggestion pill → pipeline start (`0bbdce8`)

## Mission

Patients should be able to ask educational questions without triggering a 60-second research run. When they submit a clinical case, trials should be **read and summarized for relevance**, not just listed as API metadata.

## Current gaps

1. Every message → full LangGraph pipeline (no router).
2. `TrialsAgent` → single `fetch_trials()` → thin `ClinicalTrial` records (`briefSummary` only, 500 chars); search API access fixed but no deep read.
3. Parallel readers exist only for **guideline URLs** (`ResearchCoordinatorAgent`).
4. `ReportSynthesizer` receives trial JSON blobs without eligibility analysis.

## Already on branch (do not re-implement)

| Item | Status |
|------|--------|
| `fetch_trials()` with `curl_cffi` | Done (`0bbdce8`) |
| Trials API `validation_flags` on search error | Done |
| Suggestion pills start pipeline | Done (`app/main.py`) |

## Code paths to extend

| Area | Path |
|------|------|
| UI submit | `app/main.py` → `app/chat_bridge.py` → `_submit_message()` or chat reply |
| Graph | `cdss/pipeline/workflow.py`, `nodes.py` — replace `node_trials` with `node_trials_read` |
| Trials API | `cdss/integrations/clinical_trials.py` — add `fetch_study`, `rank_trials`, `keywords` in `_parse` |
| Parallel pattern | `cdss/agents/research/coordinator_agent.py` |
| Factory | `cdss/agents/factory.py`, `cdss/core/enums.py` |
| Synthesizer input | `cdss/agents/synthesis/report_agent.py` |
| Config | `cdss/config/sources.yaml`, `registry.py` |

## Out of scope for this feature

- Replacing Serper search
- PrimeKG changes
- Unified `DocumentAggregator` (v2)
- Push to production hosting
