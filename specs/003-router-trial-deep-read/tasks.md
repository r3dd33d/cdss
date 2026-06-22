# Tasks: Router, Chat Mode, and Trial Deep-Read

**Feature**: 003-router-trial-deep-read  
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Phase 1 — Router & Chat (US1)

- [ ] T001 [P] [US1] Add `RouteDecision` model and `RouterAgent` in `cdss/agents/router/router_agent.py`
- [ ] T002 [US1] Add `ChatAgent` + prompt in `cdss/agents/chat/chat_agent.py` (educational, disclaimer)
- [ ] T003 [US1] Wire router in `app/main.py`: route before `_submit_message`; pills/PDF force research
- [ ] T004 [US1] Unit tests `tests/core/unit/agents/test_router.py` with mocked LLM classifications
- [ ] T005 [US1] AppTest or manual checklist: chat message does not spawn sidebar agent trace

**Checkpoint**: "What is HER2?" → chat reply, no pipeline run.

---

## Phase 2 — Trial search extensions (prep for US2)

- [ ] T006 [P] [US2] Add `fetch_study(nct_id)` to `cdss/integrations/clinical_trials.py`
- [ ] T007 [P] [US2] Add `rank_trials()` heuristic + tests in `tests/core/unit/integrations/test_clinical_trials_rank.py`
- [ ] T008 [US2] Add `trials:` block to `cdss/config/sources.yaml` (`max_readers`, `max_search_results`)
- [ ] T009 [US2] Add `TrialSummary` model in `cdss/core/models/trial.py` (or `trial_summary.py`)

**Checkpoint**: Rank 10 mock trials → top 5 deterministic order.

---

## Phase 3 — Trial deep-read fan-out (US2)

- [ ] T010 [US2] Add `TrialReaderAgent` — fetch study JSON, build prompt from eligibility + interventions, LLM summarize
- [ ] T011 [US2] Add `TrialsCoordinatorAgent` — search, rank, `asyncio.gather` readers (mirror research coordinator)
- [ ] T012 [US2] Register `TRIALS_COORDINATOR`, `TRIAL_READER` in `AgentType`, `runner._make_factory()`
- [ ] T013 [US2] Replace `node_trials` with `node_trials_read` in `workflow.py` / `nodes.py`
- [ ] T014 [US2] Extend `PipelineState` with `trial_summaries`, `trials_matched_count`
- [ ] T015 [US2] Unit tests `tests/core/unit/agents/test_trials_coordinator.py` — 10 hits → 5 spawns, 3 hits → 3 spawns

**Checkpoint**: Integration test with mocked CT.gov — report includes eligibility excerpts.

---

## Phase 4 — Aggregation & synthesizer (US3)

- [ ] T016 [US3] Add `TrialAggregatorAgent` — merge `TrialSummary` list into markdown section
- [ ] T017 [US3] Update `SynthesizerTask` / `ReportSynthesizerAgent` to use `trials_aggregated` + matched count
- [ ] T018 [US3] Update `report_view.py` Trials tab to show analyzed count vs matched count
- [ ] T019 [US3] Unit test synthesizer receives aggregated text, not raw JSON

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
T001 → T003 → T005
T006, T007 → T010 → T011 → T013 → T015
T016 → T017 → T019
T020 → T021
```

## Parallelizable

T001, T006, T007, T022 can start in parallel after plan approval.
