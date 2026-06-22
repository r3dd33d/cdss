# Phase 0 Research: Inline Chain-of-Thought Agent Trace

## R1 — Streaming a live block *inside* the chat turn (Streamlit)

**Decision**: While `run_status == "running"`, render an assistant turn at the bottom of the thread — `with st.chat_message("assistant"):` — and inside it run a single `@st.fragment(run_every="0.7s")`. Each tick: drain new events from the `RunHandle`, accumulate into a session buffer, call `trace_labels.derive_steps(buffer)`, and render the block via `thinking_trace.render_live(steps, status_container)` using one `st.status(current_label, state="running")`. On `handle.done()`, set the final state, append the assistant message carrying `report` + `steps`, clear the live buffer, and `st.rerun()`.

**Rationale**: `st.chat_message` puts the block in the conversation flow (FR-001); a `run_every` fragment re-renders only that block, not the whole script, giving ≤1s step latency (SC-003) without re-running the pipeline. This mirrors the existing working sidebar fragment — we relocate it, not reinvent it.

**Alternatives considered**: `st.write_stream` (token streaming) — rejected; we narrate discrete phases, not LLM tokens. Polling the whole script with `st.rerun` loops — rejected; coarser and flickers the full page.

## R2 — Reliable expand/collapse after completion (the user's bug)

**Decision**: Completed turns render a **static** thinking block from the message's stored `steps` in the history loop — NOT inside any `run_every` fragment. Use `st.status(summary_label, state="complete", expanded=False)` (or `st.expander`) listing all steps.

**Root cause of the reported bug**: the old block lived in a `run_every="0.7s"` sidebar fragment that re-created `st.status(..., expanded=False)` every 0.7s. Any user expansion was overwritten on the next tick — hence "it collapses and I can't expand it." Once the finished block is rendered outside the live fragment, Streamlit preserves the user's expand/collapse toggle across reruns (FR-008, SC-005). The live block stays auto-managed only while running.

**Alternatives considered**: keeping it in the fragment but tracking expansion in session state — rejected as needless complexity; stop re-creating it instead.

## R3 — Are the counts available without core changes?

**Decision**: **No core change required.** Derive fan-out counts by counting `AGENT_SPAWNED` events per `agent_type` in the buffer.

**Evidence**: `cdss/agents/factory.py` emits `AGENT_SPAWNED → AGENT_STARTED → AGENT_COMPLETED/FAILED` for every agent, each tagged with `agent_type` and (on completion) `duration_ms`; `runner.py` emits `RUN_STARTED/COMPLETED/FAILED`. The enum's `SOURCE_DISCOVERED`, `SOURCE_FETCHED`, `LLM_CALL`, `PHASE_COMPLETED` are **not** emitted anywhere. Per Constitution IV ("one source = one agent"), the number of `SOURCE_READER` spawns == sources read, and `TRIAL_READER` spawns == trials read. So "Reading 5 sources" / "Reviewing 3 trials" come straight from spawn counts.

**Rationale**: Honors "no core change unless a count is genuinely missing" — it isn't. Keeps the diff UI-only and the core untouched (Principle II, VI).

**Alternatives considered**: adding `SOURCE_DISCOVERED` emission with counts to the core — rejected; unnecessary and would violate the minimal-diff/UI-only scope.

## R4 — "New case" button placement

**Decision**: Keep the "New case" button in the sidebar. Only the *Agent activity* subheader and trace rendering are removed from the sidebar; the sidebar remains for "New case".

**Rationale**: Minimal diff (Principle VI). "New case" is unrelated to the relocated trace; moving it would be incidental churn.

**Alternatives considered**: moving "New case" under the chat — deferred; out of scope for this feature.

## Phase → label mapping (resolved, used by data-model & contract)

| Phase key | Triggered by `AgentType` | Friendly label | Count source |
|-----------|--------------------------|----------------|--------------|
| analyze | INTAKE | "Analyzing your question" | — |
| research | RESEARCH_COORDINATOR | "Searching guideline sources" | — |
| read_sources | SOURCE_READER (N spawns) | "Reading {N} sources" / "Spawning {N} agents to read sources" | count of SOURCE_READER spawns |
| aggregate | RESEARCH_AGGREGATOR | "Synthesizing source findings" | — |
| trials | TRIALS / TRIALS_COORDINATOR / TRIAL_READER (N) | "Reviewing {N} clinical trials" | count of TRIAL_READER spawns |
| off_label | CROSS_INDICATION_COORD / KG_TRAVERSAL / HYPOTHESIS | "Exploring off-label options" | — |
| summarize | REPORT_SYNTHESIZER | "Summarizing findings" | — |

Unknown/unmapped `agent_type` → generic "Working…" step (FR-011). Overall run framing from `RUN_STARTED` ("Starting…") and `RUN_COMPLETED`/`RUN_FAILED` (final state).
