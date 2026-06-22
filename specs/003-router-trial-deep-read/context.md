# Context: Router, Chat Mode, and Trial Deep-Read

**Feature**: 003-router-trial-deep-read  
**Depends on**: 001-cdss-multi-agent-pipeline, 002-chat-ui-layout  
**Prep commits**: trials `curl-cffi` fix, suggestion pill → pipeline start (`0bbdce8`)

## Mission

Patients should be able to ask educational questions without triggering a 60-second research run. When they submit a clinical case, trials should be **read and summarized for relevance**, not just listed as API metadata.

## Current gaps

1. Every message → full LangGraph pipeline (no router).
2. `TrialsAgent` → single `fetch_trials()` → thin `ClinicalTrial` records (`briefSummary` only, 500 chars).
3. Parallel readers exist only for **guideline URLs** (`ResearchCoordinatorAgent`).
4. `ReportSynthesizer` receives trial JSON blobs without eligibility analysis.

## Code paths to extend

| Area | Path |
|------|------|
| UI submit | `app/main.py` → `_submit_message()` |
| Graph | `cdss/pipeline/workflow.py`, `nodes.py` |
| Trials API | `cdss/integrations/clinical_trials.py` |
| Parallel pattern | `cdss/agents/research/coordinator_agent.py` |
| Factory | `cdss/agents/factory.py`, `cdss/core/enums.py` |
| Synthesizer input | `cdss/agents/synthesis/report_agent.py` |

## Out of scope for this feature

- Replacing Serper search
- PrimeKG changes
- Push to production hosting
