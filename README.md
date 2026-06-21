# CDSS — Clinical Decision Support System

> **Research and education tool only — not medical advice.**

A single Streamlit chat app that runs a 5-agent clinical research pipeline
in-process using Groq's free LLM tier: intake → standard care → clinical trials →
off-label hypotheses → plain-English report, with a live agent-trace panel.

## Quickstart

```bash
cp .env.example .env        # fill GROQ_API_KEY and SERPER_API_KEY
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
streamlit run app/main.py
```

Open http://localhost:8501, describe a diagnosis, watch agents work.

## Architecture

- **`cdss/`** — headless core (agents, pipeline, LLM, sources, KG). Never imports `streamlit`.
- **`app/`** — Streamlit chat UI. Calls the core only through `app/runner_bridge.py`.
- **`tests/`** — core tests mock all I/O; UI tests use `st.testing.AppTest` with a stubbed bridge.

See [ARCHITECTURE.md](ARCHITECTURE.md) and [specs/](specs/) for full design docs.

## Commands

```bash
make run      # streamlit run app/main.py
make test     # pytest tests/
make lint     # ruff + black
make guards   # file-size · import-direction · comment-length gates
```

## Disclaimer

This tool is for research and education only. Clinical trial eligibility must be
confirmed by a qualified physician. Never start, stop, or change treatment based
on this report alone.
