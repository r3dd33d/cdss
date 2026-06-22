# Tasks: Router, Chat Mode, and Trial Deep-Read

**Feature**: 003-router-trial-deep-read  
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Phase 1 — Router & Chat (US1)

- [ ] T001 [P] [US1] Add `RouteDecision` in `cdss/core/models/route.py` and `RouterAgent` in `cdss/agents/router/router_agent.py`
- [ ] T002 [US1] Add `ChatAgent` + prompt in `cdss/agents/chat/chat_agent.py` (educational, disclaimer; **not** in `app/`)
- [ ] T003 [US1] Add `app/chat_bridge.py` sync helpers (`asyncio.run` for `route_message` / `chat_reply`); wire in `app/main.py` before `_submit_message()`; pills/PDF force research
- [ ] T004 [US1] Unit tests `tests/core/unit/agents/test_router.py` with mocked LLM classifications
- [ ] T005 [US1] AppTest or manual checklist: chat message does not spawn sidebar agent trace
- [ ] T024 [P] [US1] [SC-001] Chat latency smoke `tests/app/unit/test_chat_latency.py` — mocked LLM, assert no `Runner.run`, completes &lt; 5 s wall clock

**Checkpoint**: "What is HER2?" → chat reply, no pipeline run.

---

## Phase 2 — Trial search extensions (prep for US2)

- [x] T006a [P] [US2] **DONE** (`0bbdce8`): `fetch_trials()` via `curl_cffi`, validation flags on API error
- [ ] T006 [P] [US2] Add `fetch_study(nct_id)` to `cdss/integrations/clinical_trials.py`
- [ ] T006b [US2] Extend `_parse()` to populate `ClinicalTrial.keywords` from `conditionsModule.keywords`
- [ ] T007 [P] [US2] Add `rank_trials()` heuristic + tests in `tests/core/unit/integrations/test_clinical_trials_rank.py`
- [ ] T008 [US2] Add `trials:` block to `cdss/config/sources.yaml` (`max_readers`, `max_search_results`, `rank_recruiting_boost`)
- [ ] T008b [US2] Extend `cdss/config/registry.py` + settings to load `trials` config into `SourceRegistry`
- [ ] T009 [US2] Add `TrialSummary` model; extend `ClinicalTrial` with `keywords: list[str]`

**Checkpoint**: Rank 10 mock trials → top 5 deterministic order.

---

## Phase 3 — Trial deep-read fan-out (US2)

- [ ] T010 [US2] Add `TrialReaderAgent` — `fetch_study`, build prompt from eligibility + interventions, LLM summarize
- [ ] T011 [US2] Add `TrialsCoordinatorAgent` — search, rank, `asyncio.gather` readers; **append validation_flag per failed reader (NCT id + error)**
- [ ] T016 [US3] Add `TrialAggregatorAgent` — merge `TrialSummary` list into markdown; note gaps when readers failed
- [ ] T012 [US2] Register `TRIALS_COORDINATOR`, `TRIAL_READER`, `TRIAL_AGGREGATOR` in `AgentType`, `runner._make_factory()`
- [ ] T013 [US2] Replace `node_trials` with `node_trials_read` in `workflow.py` / `nodes.py` — spawn coordinator **then** aggregator (mirror `node_research`); FR-002 guard: skip/empty when `state.condition` blank
- [ ] T014 [US2] Extend `PipelineState` with `trial_summaries`, `trials_matched_count`, `trials_aggregated`
- [ ] T015 [US2] [SC-002] Unit tests `tests/core/unit/agents/test_trials_coordinator.py` — 10 hits → 5 spawns, 3 hits → 3 spawns, 1 failure → flag + partial summaries
- [ ] T025 [P] [US2] [SC-004] Trace test: mocked run emits `TRIAL_READER` children under `TRIALS_COORDINATOR`, then `TRIAL_AGGREGATOR` spawn, in event bus
- [ ] T026 [US2] [FR-002, SC-002, SC-003] Integration `tests/core/integration/test_trials_read_pipeline.py`:
  - empty condition after intake → no trial readers
  - 10 mocked hits → ≤5 readers, partial failure tolerated
  - report markdown references eligibility / matched-vs-analyzed counts

**Checkpoint**: Integration test — report includes eligibility excerpts and "N matched; M analyzed" copy.

---

## Phase 4 — Synthesizer & UI (US3)

- [ ] T017 [US3] Update `SynthesizerTask` / `ReportSynthesizerAgent` to use `trials_aggregated` + `trials_matched_count` (not raw trial JSON)
- [ ] T018 [US3] Update `report_view.py` Trials tab to show analyzed count vs matched count
- [ ] T019 [US3] [SC-002] Unit test synthesizer: receives aggregated text; prompt/body includes matched count and analyzed count when they differ

**Checkpoint**: Full research run — trials section discusses eligibility fit.

---

## Phase 5 — Polish (US4, optional)

- [ ] T020 [P] [US4] Store `last_report` in session; chat agent includes summary context
- [ ] T021 [US4] Router follow-up: "trial 2 from my report" → chat with NCT context
- [ ] T022 [P] Update `ARCHITECTURE.md` pipeline diagram and agent list
- [ ] T023 [P] Update `quickstart.md` for this feature

---

## Dependencies

```text
T001 → T003 → T005, T024
T006a (done) → T006 → T006b → T007
T008 → T008b → T011
T006b, T007, T009 → T010 → T011 → T016 → T012 → T013 → T015, T025, T026
T013, T014 → T017 → T019
T020 → T021
```

## Parallelizable

T001, T006, T006b, T007, T022, T024 can start in parallel after plan approval.
