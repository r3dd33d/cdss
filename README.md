# CDSS — Clinical Decision Support System

> **Research and education tool only — not medical advice.**

A single Streamlit chat app that runs a 5-agent clinical research pipeline
in-process using Groq's free LLM tier: intake → standard care → clinical trials →
off-label hypotheses → plain-English report, with a live agent-trace panel.

## Quickstart

Requires **Python 3.11+**. All commands below use the project `.venv` only.

```bash
cp .env.example .env        # fill GROQ_API_KEY and SERPER_API_KEY
make setup                  # create .venv + install dependencies
./run                       # or: make run
```

Open http://localhost:8501, describe a diagnosis, watch agents work.

> Do **not** run bare `streamlit run` — macOS may pick a system Python 3.9.
> Always use `./run`, `make run`, or `.venv/bin/python -m streamlit run app/main.py`.

## Architecture

- **`cdss/`** — headless core (agents, pipeline, LLM, sources, KG). Never imports `streamlit`.
- **`app/`** — Streamlit chat UI. Calls the core only through `app/runner_bridge.py`.
- **`tests/`** — core tests mock all I/O; UI tests use `st.testing.AppTest` with a stubbed bridge.

See [ARCHITECTURE.md](ARCHITECTURE.md) and [specs/](specs/) for full design docs.

## Commands

```bash
make setup    # create .venv + pip install (first time)
make run      # ./scripts/run.sh → venv streamlit only
make test     # venv pytest
make lint     # venv ruff + black
make guards   # venv guard scripts
```

## Disclaimer

This tool is for research and education only. Clinical trial eligibility must be
confirmed by a qualified physician. Never start, stop, or change treatment based
on this report alone.
