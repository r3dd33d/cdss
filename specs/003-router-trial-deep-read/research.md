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
ranked = rank_trials(candidates, profile, limit=MAX_READERS)
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

**Decision**: Deterministic score on **search-result metadata** (`ClinicalTrial`) before per-study fetch:

| Signal | Weight |
|--------|--------|
| `status == RECRUITING` | +2 |
| Phase string contains `PHASE3` or `PHASE2` | +1 each |
| Biomarker gene in `title` or `keywords` | +2 per match |
| Condition token overlap in `title` | +1 |

`keywords` populated in `_parse()` from `conditionsModule.keywords` (task T006b). Take top `max_readers`; pass `trials_matched_count` to synthesizer for "10 matched, 5 analyzed" copy.

**Alternatives considered**:
- LLM ranker — extra call, slower; use in v2 if heuristic quality insufficient
- API order only — poor relevance for broad searches
- Rank after full study fetch — too many API calls before narrowing

## Decision 6: Aggregator shape

**Decision**: **Two aggregators in v1**: existing `ResearchAggregatorAgent` for guidelines + new `TrialAggregatorAgent` for trials. Synthesizer receives both strings.

**Rationale**: Different prompts (eligibility fit vs standard of care). Unified `DocumentAggregator` deferred to v2 per spec non-goals.

## Decision 7: Chat agent

**Decision**: `ChatAgent` in `cdss/agents/chat/` (not `app/`). System prompt: educational only, not medical advice, suggest submitting a full case for research report.

**Rationale**: FR-010 + Constitution II (no LLM logic in `app/`).

## Decision 8: HTTP client for CT.gov

**Decision**: Keep `curl_cffi.AsyncSession` with `impersonate="chrome"` for search and per-study fetch.

**Rationale**: `httpx` returns 403 (verified 2026-06-22); search fix landed in `0bbdce8`.

## Decision 9: LangGraph node shape

**Decision**: Single `node_trials_read` wrapping `TrialsCoordinatorAgent` (search + rank + fan-out inside coordinator). No separate `trials_search` graph node.

**Rationale**: Matches research phase (coordinator owns discovery + fan-out); fewer graph edges.

## Decision 10: Factory scope (FR-007)

**Decision**: Router and Chat are pre-pipeline modules called directly with `LLMClient`; pipeline agents use `AgentFactory.spawn()`.

**Rationale**: Router/chat are not part of LangGraph state machine; avoids polluting run tree with a classify step before `RUN_STARTED`. Optional lightweight UI events for route/chat.
