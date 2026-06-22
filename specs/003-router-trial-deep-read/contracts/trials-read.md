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

Returns metadata for **all** matches up to `max_results`.

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
```

## Reader spawn rule

```text
N = min(len(ranked_trials), max_readers)   # max_readers default 5
```

If `len(ranked_trials) == 0`, spawn 0 readers.

## Failure semantics

- Search error → `validation_flags`, empty trials, no readers
- Reader error → `None` in gather results; excluded from summaries; flag optional per failure
- Parse error on one study → skip that study; continue

## Synthesizer input

Report synthesizer receives:
- `trials_aggregated: str` (from TrialAggregator)
- `trials_matched_count: int`
- `trial_summaries: list[TrialSummary]` (for trace/debug)
