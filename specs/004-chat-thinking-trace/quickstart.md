# Quickstart: Verify the Inline Chain-of-Thought Trace

## Run

```bash
cd /Users/idaniel/Downloads/CDSS-DS
./run            # or: make run  (streamlit on :8501)
```

## Manual verification (maps to acceptance scenarios)

1. **Inline trace appears (US1 / FR-001)**: Submit "Stage III NSCLC, EGFR exon 19 deletion, on osimertinib, no prior chemo". A thinking block appears **in the chat thread** (not the sidebar) and advances: Analyzing → Searching sources → Reading N sources → Reviewing trials → Exploring off-label → Summarizing.
2. **Readable labels (FR-003 / SC-002)**: No raw text like `run_started` or `AGENT_SPAWNED` is visible anywhere.
3. **Fan-out counts (US2 / FR-005)**: The "Reading N sources" / "Reviewing N trials" counts match the run (cross-check against the final report's source/trial counts).
4. **Report below trace (FR-006)**: When done, the final report renders in the same assistant turn, directly below the completed thinking block.
5. **Expand/collapse persists (US3 / FR-008 / SC-005)**: Collapse the completed block, interact elsewhere (e.g. type a follow-up) — it stays collapsed. Expand it — all steps remain listed. It never auto-collapses on its own.
6. **Multiple turns (FR-009)**: Run a second case; each assistant turn keeps its own thinking block + report.
7. **Conversational reply (FR-010)**: After a report exists, ask a short follow-up that routes to chat — no thinking block appears.
8. **Failure path (FR-007)**: Temporarily break the run (e.g. invalid key) → the block shows the in-progress step as failed with a readable error.
9. **Sidebar cleaned (removal)**: The sidebar shows only "New case" — no "Agent activity" panel.

## Automated checks

```bash
.venv/bin/python -m pytest tests/app/unit/test_trace_labels.py -q   # pure label/step logic
.venv/bin/python -m pytest -q                                        # full suite stays green
grep -rn "agent_trace\|_render_sidebar_trace" app/                   # expect: no matches (removed)
make guards                                                          # file-size, import-direction, comment-length
```

## Done when

All 9 manual checks pass, `test_trace_labels.py` passes, the grep returns nothing, and `cdss/` still never imports Streamlit.
