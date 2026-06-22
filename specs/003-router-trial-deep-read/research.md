# Research: Router, Chat Mode, and Trial Deep-Read

**Feature**: 003-router-trial-deep-read | **Date**: 2026-06-22

## Decision 1: Router placement

**Decision**: Implement `RouterAgent` in `cdss/agents/router/`, invoked from `app/main.py` before `start_run()`.

**Rationale**: Keeps classification logic testable and out of Streamlit; UI only branches on `RouteDecision.mode`.

**Alternatives considered**:
- LangGraph entry conditional — heavier for a single LLM call; defer to v2 if router needs memory
- Streamlit-only heuristics (regex) — brittle for natural language

## Decision 2: Router output schema

**Decision**: Structured JSON:

```json
{
  "mode": "chat" | "research" | "clarify",
  "confidence": 0.0,
  "clarifying_question": ""
}
```

**Rationale**: One cheap LLM call; no tool loop; aligns with Plan-and-Execute gate pattern.

## Decision 3: Trial reader fan-out

**Decision**: Mirror `ResearchCoordinatorAgent`:

```python
ranked = rank_trials(candidates, profile)[:MAX_READERS]
summaries = await asyncio.gather(*[spawn_reader(t) for t in ranked])
```

Spawn count = `len(ranked)` where `len(ranked) <= MAX_READERS`.

**Rationale**: Proven pattern in codebase; same semaphore and isolated-failure semantics.

## Decision 4: Trial content source

**Decision**: Per-study `GET /api/v2/studies/{nctId}`; reader prompt uses:
- `eligibilityModule.eligibilityCriteria`
- `descriptionModule.briefSummary` + `detailedDescription`
- `armsInterventionsModule.interventions`
- `conditionsModule.conditions` / keywords

**Rationale**: No HTML scraping; full criteria live in API JSON (confirmed on NCT06001086).

## Decision 5: Ranking when &gt; 5 trials

**Decision**: Deterministic score before fan-out:

| Signal | Weight |
|--------|--------|
| `overallStatus == RECRUITING` | +2 |
| Phase contains PHASE3 or PHASE2 | +1 each |
| Title/keywords contain biomarker gene | +2 per match |
| Title contains condition token overlap | +1 |

Take top 5; pass `trials_matched_count` to synthesizer for "10 matched, 5 analyzed" copy.

**Alternatives considered**:
- LLM ranker — extra call, slower; use in v2 if heuristic quality insufficient
- API order only — poor relevance for broad searches

## Decision 6: Aggregator shape

**Decision**: Add `TrialAggregatorAgent` separate from `ResearchAggregatorAgent` in v1; synthesizer receives both aggregated strings.

**Rationale**: Different prompts (eligibility fit vs standard of care); can merge into `DocumentAggregator` later.

## Decision 7: Chat agent

**Decision**: `ChatAgent` with system prompt: educational only, not medical advice, suggest submitting a full case for research report.

**Rationale**: FR-010 — no external APIs in chat mode.

## Decision 8: HTTP client for CT.gov

**Decision**: Keep `curl_cffi.AsyncSession` with `impersonate="chrome"` for search and per-study fetch.

**Rationale**: `httpx` returns 403 (verified 2026-06-22); already fixed in feature prep commit.
