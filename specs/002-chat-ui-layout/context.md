# Feature Context

**Feature**: Redesign the Streamlit chat UI layout — bottom-anchored input, full-width conversation column, agent activity in sidebar, uniform example prompts.
**Mission**: Make the clinical research assistant feel like a standard AI chat product without changing pipeline behavior from feature 001.
**Code Paths**: app/main.py (layout wiring), app/components/suggestions.py (example chips), app/components/agent_trace.py (sidebar trace), app/components/disclaimer.py (compact banner); runner_bridge and session state unchanged.
**Directives**: Governed by `.specify/memory/constitution.md` (v2.0.0 — Streamlit-only, UI/core separation). Presentation-only; no changes to `cdss/` agents, events, or runner contract.
**Research**: Streamlit chat layout best practices — `st.chat_input` must be last in main column; `st.sidebar` for agent trace; `st.pills` or fixed-height bordered containers for uniform example chips; `st.fragment` refresh preserved for live trace.
