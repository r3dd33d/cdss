# Quickstart: Developing 003-router-trial-deep-read

## Branch

```bash
git checkout -b 003-router-trial-deep-read
```

## Prerequisites

```bash
make setup
cp .env.example .env   # GROQ_API_KEY, SERPER_API_KEY
```

## Verify trials API (manual)

```bash
.venv/bin/python -c "
import asyncio
from cdss.integrations.clinical_trials import fetch_trials
async def main():
    trials, err = await fetch_trials('HER2-positive breast cancer', ['HER2'])
    print(len(trials), err)
asyncio.run(main())
"
```

## Run app

```bash
./run
```

## Test targets (as implemented)

```bash
make test
# Phase 1:
.venv/bin/python -m pytest tests/core/unit/agents/test_router.py tests/app/unit/test_chat_latency.py -v
# Phase 2–3:
.venv/bin/python -m pytest tests/core/unit/integrations/test_clinical_trials_rank.py tests/core/unit/agents/test_trials_coordinator.py -v
.venv/bin/python -m pytest tests/core/integration/test_trials_read_pipeline.py -v
```

## Manual checks

1. **Chat path**: Ask "What is HER2?" — quick educational reply, no sidebar agent trace.
2. **Research path**: Use a suggestion pill or describe a case — full pipeline including trial deep-read.
3. **Trials tab**: After a research run, Trials tab shows matched vs analyzed counts.

## Already done on this branch

- `fetch_trials()` + `curl_cffi` (task T006a)
- Suggestion pills start the pipeline
- Router + ChatAgent + trial deep-read pipeline (feature 003)
