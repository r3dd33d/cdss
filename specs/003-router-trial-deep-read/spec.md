# Feature Specification: Router, Chat Mode, and Trial Deep-Read Pipeline

**Feature Branch**: `003-router-trial-deep-read`  
**Created**: 2026-06-22  
**Status**: Draft  
**Input**: Extend the CDSS pipeline with (1) a router that distinguishes casual chat from research requests, (2) a **trial** deep-read phase matching the existing guideline fan-out pattern, and (3) topic-specific aggregation into a unified report. Trial readers spawn `min(ranked_trial_count, MAX_READERS)` in parallel (MAX_READERS = 5 by default). Guideline parallel readers (up to 5 `SourceReader` agents) remain unchanged from feature 001.

## Overview

Today every user message triggers the full research pipeline. Trials are fetched as thin API metadata only — eligibility criteria and interventions are never read. Guideline research already fans out up to five `SourceReader` agents in parallel (feature 001), but trials do not.

This feature adds an **intent router** at the UI boundary, preserves a lightweight **chat path** for non-research messages, and introduces a **trial deep-read phase** that mirrors the existing research coordinator pattern: search → rank → bounded parallel read → aggregate → synthesize.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Router sends chat vs research (Priority: P1) 🎯 MVP

A user types "What does HER2 positive mean?" and receives a short educational reply without spawning the research pipeline. A user types "HER2-positive breast cancer, stage II, no current treatment" (or clicks an example pill) and the full research pipeline runs.

**Why this priority**: Avoids wasted API calls and confusing "empty reports" for conversational input.

**Independent Test**: Mock the router LLM to return `chat` vs `research`; assert chat path never calls `Runner.run()` and research path does.

**Acceptance Scenarios**:

1. **Given** a general educational question with no patient case, **When** the user submits it, **Then** the router selects `chat` mode and returns an assistant message without a pipeline run.
2. **Given** a structured patient case or explicit trial/search intent, **When** the user submits it, **Then** the router selects `research` mode and starts the existing runner bridge.
3. **Given** an ambiguous message ("help me"), **When** the user submits it, **Then** the router selects `clarify` mode and asks one short follow-up question without starting a run.

---

### User Story 2 - Trial deep-read with dynamic fan-out (Priority: P1)

After intake and trial search, the system spawns one **TrialReader** agent per top-ranked trial, up to five concurrent readers. Each reader fetches the full study record (`GET /api/v2/studies/{nctId}`), extracts eligibility and interventions, and summarizes relevance to the patient profile.

**Why this priority**: Core clinical value — patients need eligibility fit, not just trial titles.

**Independent Test**: Mock ClinicalTrials.gov search (10 hits) and per-study fetch; assert exactly 5 readers spawn, 5 summaries returned, and report mentions total matched count.

**Acceptance Scenarios**:

1. **Given** 10 recruiting trials returned from search, **When** the trial read phase runs, **Then** exactly 5 TrialReader agents spawn (top 5 by rank) and the report states "10 matched; 5 analyzed in detail."
2. **Given** 3 recruiting trials, **When** the trial read phase runs, **Then** 3 TrialReader agents spawn (not 5).
3. **Given** 0 trials, **When** the trial read phase runs, **Then** no readers spawn and the report trials section explains no matches.
4. **Given** one TrialReader fails (timeout), **When** the phase completes, **Then** other readers still contribute and a validation flag records that specific failure (NCT id + error).

---

### User Story 3 - Topic-specific aggregation before synthesis (Priority: P2)

In v1, **two aggregators** feed the final synthesizer (not a single merged agent):

- **ResearchAggregatorAgent** (existing) — merges guideline `SourceSummary` excerpts into standard-of-care text.
- **TrialAggregatorAgent** (new) — merges `TrialSummary` list into a clinical-trials markdown section.

The **ReportSynthesizer** receives both pre-aggregated strings plus counts, not raw API JSON.

**Why this priority**: Without aggregation, the synthesizer receives raw JSON blobs and quality is inconsistent.

**Independent Test**: Feed 3 source summaries + 2 trial summaries to their respective aggregators; assert structured markdown sections out.

**Acceptance Scenarios**:

1. **Given** partial reader failures, **When** aggregation runs, **Then** each aggregator uses only successful summaries and notes gaps.
2. **Given** completed aggregation, **When** the synthesizer runs, **Then** it receives pre-aggregated trial and guideline text, not raw API JSON.

---

### User Story 4 - Follow-up on prior report (Priority: P3)

A user asks "Tell me more about trial 2 from my last report" in chat mode. The router selects `chat` with report context, or narrow `research` scoped to one NCT ID.

**Why this priority**: Natural conversation after a run; can defer to chat-with-context in v1.

**Independent Test**: Session with stored `last_report`; follow-up question answered referencing NCT id from report.

---

## Functional Requirements

- **FR-001**: Router MUST classify each user message as `chat`, `research`, or `clarify` before invoking the pipeline.
- **FR-002**: Research mode MUST run intake before any search or read phase; the trials node MUST NOT execute until `condition` is populated by intake.
- **FR-003**: Trial search MUST use ClinicalTrials.gov v2 via `curl_cffi` (TLS-safe client). *(Search portion complete on branch `0bbdce8`; per-study fetch remains.)*
- **FR-004**: Trial deep-read MUST fetch per-study records including `eligibilityModule.eligibilityCriteria`.
- **FR-005**: **Trial** parallel readers MUST be capped at `MAX_READERS` (default 5) via semaphore; spawn count = `min(ranked_trial_count, MAX_READERS)`. Guideline `SourceReader` cap remains `max_total_sources: 5` from feature 001 (separate pool).
- **FR-006**: Trial ranking MUST occur before fan-out when candidates exceed `MAX_READERS`, using metadata on `ClinicalTrial` (title, status, phase, keywords).
- **FR-007**: All **pipeline** agent spawns (intake through synthesizer) MUST go through `AgentFactory.spawn()` and emit trace events. Router and chat are pre-pipeline LLM classifiers/responders in `cdss/agents/` invoked via `route_message()` / `chat_reply()` — they are exempt from factory spawn but MAY emit lightweight trace events from the UI layer.
- **FR-008**: Reader failures MUST be isolated; one failure MUST NOT abort the run.
- **FR-009**: API and reader errors MUST surface as `validation_flags`, not silent empty results; each failed TrialReader MUST append a flag naming the NCT id.
- **FR-010**: Chat mode MUST NOT call external search or ClinicalTrials.gov APIs.
- **FR-011**: Medical disclaimer MUST remain on every research report and in the chat agent system prompt.

## Non-Goals (v1)

- Multi-turn ReAct planner that dynamically picks tools each step
- User authentication or saved case history across sessions
- Replacing LangGraph with a fully autonomous agent loop
- Reading more than 5 **trials** in depth per run (mention-only for the rest)
- Single unified `DocumentAggregator` merging guidelines + trials (deferred to v2)

## Success Criteria

- SC-001: Educational chat messages complete in &lt; 5 s without pipeline spawn
- SC-002: Research run with 10 trial hits spawns ≤ 5 readers and completes with partial-failure tolerance
- SC-003: Trial section of report references eligibility criteria for analyzed trials
- SC-004: Sidebar trace shows TrialReader children spawned under TrialsCoordinator
