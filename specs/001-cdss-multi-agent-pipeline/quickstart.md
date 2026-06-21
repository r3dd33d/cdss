# Quickstart — Dev Workflow

> Research/education tool only — **not medical advice**.

A single Streamlit app: a headless `cdss/` core runs the agent pipeline in-process and
the `app/` chat UI renders it. No FastAPI, no separate server (Constitution v2.0.0).

## Prerequisites

- Python 3.11+
- A free **Groq** API key (`gsk_…`) and a search key (e.g. Serper)
- (optional) Docker for Qdrant; PrimeKG downloads on first cross-indication run

## One-time setup

```bash
cp .env.example .env          # fill GROQ_API_KEY, SERPER_API_KEY
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

The core (`cdss/`) and UI (`app/`) share one environment; the import-direction guard
keeps `cdss/` free of any `streamlit` import.

## Run

```bash
# One process — the chat app drives the agents in-process
streamlit run app/main.py
```

Open the URL Streamlit prints (default http://localhost:8501), describe a case in the
chat input (or attach a PDF), and watch the live agent trace while the report streams in.

## Smoke check (core, no UI)

```bash
python -c "
import asyncio
from cdss.config.settings import load_settings
from cdss.pipeline.runner import build_runner
r = build_runner(load_settings())
report = asyncio.run(r.run('Stage III NSCLC, EGFR exon 19 deletion, on osimertinib'))
print(report.markdown[:500])
"
```

## Tests & gates

```bash
pytest tests/core tests/app -v
# Constitution gates (CI):
#  - file-size:        no cdss/** or app/** file > 400 lines
#  - import-direction: cdss/** must NOT import streamlit
#  - comment-length:   no comment longer than two sentences
#  - disclaimer:       every produced report contains the medical disclaimer
```

Core tests mock LLM/HTTP/CT.gov/KG and never import `streamlit`; UI tests use
`st.testing.AppTest` with a stubbed `runner_bridge` and never run real agents.

## Config knobs (no code changes — Constitution III/§Config)

Edit `cdss/config/sources.yaml`: toggle guideline sites, switch search provider, adjust
`max_total_sources` / fetch timeout, reorder `model_preference`, set token budgets.

## Map to the notebook

`CDSS_Pipeline_Colab.ipynb` cells → modules: state→`core/models`+`pipeline/state`; LLM
(Cell 8)→`llm/`; KG (14/16)→`knowledge/graph`; trials (22)→`integrations/clinical_trials`;
each `agent_*`→`agents/<pkg>`; graph (28)→`pipeline/workflow`; run loop (30–34)→
`pipeline/runner` (core) + `app/runner_bridge` + `app/main.py` (UI).
