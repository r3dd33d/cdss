# Phase 1 — Data Model

Pure-domain Pydantic v2 models live in `cdss/core/models/` (no I/O). The LangGraph
shared state lives in `cdss/pipeline/state.py`. The Streamlit UI consumes these core
models directly through `runner_bridge` — there is no separate wire-DTO layer (no
HTTP boundary under the Streamlit-only architecture).

## Enums (`core/enums.py`)

- **AgentType**: `INTAKE`, `RESEARCH_COORDINATOR`, `SOURCE_READER`, `RESEARCH_AGGREGATOR`,
  `TRIALS`, `CROSS_INDICATION_COORD`, `KG_TRAVERSAL`, `HYPOTHESIS`, `REPORT_SYNTHESIZER`.
- **RunStatus**: `RUNNING`, `COMPLETED`, `FAILED`.
- **EventType**: `RUN_STARTED`, `AGENT_SPAWNED`, `AGENT_STARTED`, `SOURCE_DISCOVERED`,
  `SOURCE_FETCHED`, `LLM_CALL`, `AGENT_COMPLETED`, `AGENT_FAILED`, `PHASE_COMPLETED`,
  `RUN_COMPLETED`, `RUN_FAILED`.

## Domain entities (`core/models/`)

### Biomarker (`patient.py`)
| Field | Type | Notes |
|-------|------|-------|
| gene | str | e.g. "EGFR" |
| variant_type | str | e.g. "exon 19 deletion" |
| details | str | free text |

### PatientProfile (`patient.py`)
| Field | Type | Notes |
|-------|------|-------|
| condition | str | "" if not extracted |
| stage | str | "" if not extracted |
| biomarkers | list[Biomarker] | default [] |
| current_medications | list[str] | default [] |
| prior_therapies | list[str] | default [] |

> Intake MUST NOT invent fields; absent info stays empty (FR-002).

### SourceRef / SourceSummary (`source.py`)
- **SourceRef**: `url`, `title`, `site_id`, `rank: int`.
- **SourceSummary**: `source: SourceRef`, `relevant_excerpt: str`, `confidence: float`
  (0.0–1.0), `fetch_duration_ms: int`, `agent_run_id: str` (links to trace tree).

### ClinicalTrial (`trial.py`)
`nct_id`, `title`, `phase`, `status`, `locations: list[str]`, `eligibility_summary`,
`url`. (Mirrors notebook Cell 22 / ClinicalTrials.gov v2.)

### OffLabelHypothesis (`hypothesis.py`)
`drug_name`, `approved_indication`, `shared_mechanism`, `evidence_level: int` (1=in-vitro,
2=animal, 3=Phase I/II, 4=Phase III adjacent), `evidence_label: str`, `citation: str`.

### FinalReport (`report.py`)
`markdown: str` (includes disclaimer — FR-007), `profile: PatientProfile`,
`sources: list[SourceRef]`, `trials_count: int`, `hypotheses_count: int`,
`validation_flags: list[str]`.

## Observability models (`observability/events.py`)

`AgentEvent` base + typed subclasses (`AgentSpawned`, `SourceFetched`, …):
`event_type: EventType`, `run_id: str`, `parent_run_id: str | None`,
`agent_type: AgentType | None`, `label: str`, `timestamp: datetime`,
`duration_ms: int | None`, `payload: dict`. `RunContext` carries `run_id`,
`parent_id`, `depth`. PII is redacted before an event is stored/streamed.

## Pipeline state (`pipeline/state.py`)

LangGraph shared `PipelineState` (Pydantic) — superset that flows through nodes:

```
run_id: str
raw_input: str
input_is_pdf: bool = False
# intake
condition, stage: str = ""
biomarkers: list[Biomarker] = []
current_medications, prior_therapies: list[str] = []
# research
source_summaries: list[SourceSummary] = []
standard_care_summary: str = ""
# trials
clinical_trials: list[ClinicalTrial] = []
# cross-indication
off_label_hypotheses: list[OffLabelHypothesis] = []
# synthesis
validation_flags: list[str] = []
final_report: str = ""
# control (notebook retry rule)
retry_count: int = 0
max_retries: int = 2
```

## Agent task/result contracts (`agents/base.py`)

- **AgentTask** (base): carries the slice of state an agent needs (kept narrow per agent).
  e.g. **SourceReaderTask**: `question`, `condition`, `stage`, `source: SourceRef`.
- **AgentResult** (base): typed output an agent returns (e.g. `SourceSummary`,
  `PatientProfile`, `list[ClinicalTrial]`, `FinalReport`) + `run_id` + optional flags.

## Lifecycle / state transitions

- **Run**: `RUNNING` → (`COMPLETED` | `FAILED`). A run with some failed sources still
  reaches `COMPLETED` with partial results (SC-003).
- **Retry rule** (FR-011): after synthesis, if `validation_flags` contain critical errors
  and `retry_count < max_retries (2)`, increment and re-enter `intake`; else `done`.
- **Phases**: `intake → research → trials → cross_indication → synthesize → END`;
  `cross_indication` is skipped when `KG_AVAILABLE` is false.
