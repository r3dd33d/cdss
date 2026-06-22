# Contract: Trials Search + Deep Read

**Feature**: 003-router-trial-deep-read

## Search

```python
async def fetch_trials(
    condition: str,
    biomarker_genes: list[str],
    *,
    max_results: int = 10,
) -> tuple[list[ClinicalTrial], str | None]:
    ...
```

Returns metadata for **all** matches up to `max_results`. **Implemented** on branch (`0bbdce8`) with `curl_cffi`.

`ClinicalTrial` includes `keywords: list[str]` from search `_parse()` for ranking.

## Per-study fetch

```python
async def fetch_study(nct_id: str) -> dict | None:
    """Full protocolSection JSON for one NCT ID."""
```

Uses `curl_cffi` + `impersonate="chrome"`.

## Ranking

```python
def rank_trials(
    trials: list[ClinicalTrial],
    profile: PatientProfile,
    *,
    limit: int = 5,
) -> list[ClinicalTrial]:
    ...
```

Inputs: `title`, `status`, `phase`, `keywords` on each `ClinicalTrial` plus profile condition/biomarkers. Does **not** require per-study fetch.

## Coordinator fan-out

```python
class TrialsCoordinatorAgent:
    async def run(task: TrialsCoordinatorTask, ctx) -> AgentResult:
        # 1. fetch_trials → all matched
        # 2. rank_trials → top limit
        # 3. asyncio.gather TrialReader per ranked trial
        # 4. return data={
        #      clinical_trials: all_matched,
        #      trial_summaries: successful_reads,
        #      trials_matched_count: len(all_matched),
        #    }
        #    validation_flags: search errors + per-reader failures
```

Invoked from single LangGraph node `node_trials_read` (after intake populated `condition`):

1. `factory.spawn(TRIALS_COORDINATOR, …)` → `trial_summaries`, `clinical_trials`, `trials_matched_count`, flags
2. `factory.spawn(TRIAL_AGGREGATOR, …)` → `trials_aggregated`

Same two-step pattern as `node_research` (coordinator → aggregator).

## Reader spawn rule

```text
N = min(len(ranked_trials), max_readers)   # max_readers default 5
```

Separate from guideline `SourceReader` pool (`max_total_sources: 5`).

If `len(ranked_trials) == 0`, spawn 0 readers.

## Failure semantics

- Search error → `validation_flags`, empty trials, no readers
- Reader error → `None` in gather results; excluded from summaries; **MUST** append `validation_flags` entry: `"TrialReader failed for {nct_id}: {error}"`
- Parse error on one study during read → skip that study; continue; append flag

## Synthesizer input

Report synthesizer receives:
- `standard_care` — from existing `ResearchAggregatorAgent`
- `trials_aggregated: str` — from `TrialAggregatorAgent`
- `trials_matched_count: int`
- `trial_summaries: list[TrialSummary]` (optional debug/trace)

Not raw `ClinicalTrial` JSON blobs.
