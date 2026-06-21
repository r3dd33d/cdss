# Feature Context

**Feature**: Production multi-agent clinical decision support pipeline ported from the Colab notebook into a single deep-module Streamlit application (headless `cdss/` core + `app/` chat UI).
**Mission**: Turn the 5-agent CDSS Colab notebook into a scalable, observable, research-only Streamlit app where a chat UI runs the agent pipeline in-process over a free Groq model and renders a live agent-trace tree.
**Code Paths**: cdss/ core (config, core, observability, llm, sources, knowledge, integrations, agents, pipeline); app/ chat UI (runner_bridge, components, state)
**Directives**: Governed by `.specify/memory/constitution.md` (v2.0.0 — Streamlit-only, no FastAPI). Baseline behavior defined by `CDSS_Pipeline_Colab.ipynb` and `ARCHITECTURE.md` (its FastAPI/REST/SSE transport superseded).
**Research**: Groq runtime model availability + preference order; site-scoped search provider choice; PrimeKG load/caching; in-process event delivery to the UI; non-blocking Streamlit run (background thread) + `st.fragment` refresh.
