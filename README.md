---
title: Frugal Api Economy Environment Server
emoji: 🏦
colorFrom: green
colorTo: blue
sdk: docker
pinned: false
app_port: 8000
base_path: /web
tags:
  - openenv
  - optimization
  - reinforcement-learning
---
# 🏦 The Frugal Architect: API Economy Simulator

> A cost-aware reinforcement learning environment for training agents that solve research tasks while minimizing API spend.

In real-world SaaS applications, LLMs often waste money by over-using expensive tools. This [OpenEnv](https://github.com/openenv) environment tests whether an AI agent can hit a confidence target while keeping costs as low as possible. Each episode starts with a fixed budget and a research goal. The agent picks tools with different cost/gain tradeoffs — and gets rewarded for efficiency, not just correctness.

---

## Table of Contents

- [Environment Overview](#environment-overview)
- [Action Space](#action-space)
- [Observation Space](#observation-space)
- [Reward Structure](#reward-structure)
- [Tasks](#tasks)
- [Baseline Performance](#baseline-performance)
- [Project Architecture](#project-architecture)
- [Setup & Installation](#setup--installation)
- [Running the Server](#running-the-server)
- [Running the Inference Agent](#running-the-inference-agent)
- [Running with Docker](#running-with-docker)
- [Environment Variables](#environment-variables)
- [Web Dashboard](#web-dashboard)
- [Python Client Usage](#python-client-usage)
- [API Endpoints](#api-endpoints)
- [Development](#development)

---

## Environment Overview

**Name:** `frugal_api_economy`  
**Type:** Single-agent, episodic, turn-based  
**Goal:** Reach a target confidence level before running out of budget  
**Difficulty range:** Easy → Hard (3 tasks with decreasing budgets and increasing confidence targets)

Each episode proceeds as follows:

1. Agent calls `/reset` with a `task_id` (1, 2, or 3)
2. Environment returns an initial observation with budget, confidence, and task description
3. Agent selects a tool + query at each step via `/step`
4. Environment deducts cost, increments confidence, and returns a reward
5. Episode terminates when confidence target is reached (success) or budget hits zero (bankruptcy)

---

## Action Space

The agent submits a `FrugalApiEconomyAction` at each step:

| Field | Type | Description |
|---|---|---|
| `tool_name` | `Literal["SCRAPE", "SEARCH", "LLM_REASON", "VERIFY"]` | The tool to invoke |
| `query` | `str` (3–512 chars) | Plain-English description of what to research |

### Available Tools

| Tool | Cost | Confidence Gain | Notes |
|---|---|---|---|
| `SCRAPE` | $0.01 | +0.20 | Cheapest option; good for early-stage, low-cost orientation |
| `LLM_REASON` | $0.05 | +0.25 | Structured reasoning; useful for synthesis |
| `SEARCH` | $0.10 | +0.40 | High-value retrieval; best cost-to-gain ratio overall |
| `VERIFY` | $0.20 | +0.60 | Highest single-step gain; **locked until confidence ≥ 0.50** |

> **VERIFY gate:** If the agent calls `VERIFY` with confidence below `0.50`, the tool is blocked. The cost is still deducted, but no confidence is gained — making it a pure penalty.

---

## Observation Space

After each `reset()` or `step()`, the environment returns a `FrugalApiEconomyObservation`:

| Field | Type | Range | Description |
|---|---|---|---|
| `budget_remaining` | `float` | `[0.0, 1.0]` | USD remaining in the wallet (normalized to starting budget) |
| `confidence` | `float` | `[0.0, 1.0]` | Cumulative research confidence accumulated so far |
| `info` | `str` | — | Human-readable summary of the last tool result |
| `termination_reason` | `str` | — | `"confidence_reached"`, `"budget_depleted"`, or `""` if still running |
| `done` | `bool` | — | `True` when the episode has ended |
| `reward` | `float` | — | Reward for the most recent step |
| `metadata` | `dict` | — | Extended info: `task_id`, `target_confidence`, `grader_score`, `tool`, `cost`, `step_count`, `episode_return`, `total_spent`, `action_history` |

---

## Reward Structure

Rewards are **non-sparse and shaped** to encourage efficient tool use:

| Event | Reward |
|---|---|
| Any tool use | `-(cost × 50)` — cost penalty applied every step |
| Reaching target confidence | `+100.0` — completion bonus |
| Budget depleted without success | `-50.0` — bankruptcy penalty |
| VERIFY blocked (confidence < 0.50) | Cost deducted, no confidence gain — effective double penalty |

**Examples:**

- `SCRAPE` used successfully: `-(0.01 × 50) = -0.50` per step
- `SEARCH` used successfully: `-(0.10 × 50) = -5.00` per step
- Reaching target: above penalties + `+100.0`

This means the agent is incentivized to reach confidence with the **fewest and cheapest tools possible**. An agent that uses `SCRAPE` twice and `SEARCH` once to hit target confidence will outscore one that spams `SEARCH` or wastes a `VERIFY` call too early.

### Grader Score

The grader score is a continuous value in `[0.0, 1.0]` available in `metadata["grader_score"]`:

```
grader_score = min(1.0, confidence / target_confidence)
```

It reaches `1.0` only when the agent meets or exceeds the target confidence.

---

## Tasks

Three tasks are available with increasing difficulty:

| Task | ID | Starting Budget | Target Confidence | Research Goal |
|---|---|---|---|---|
| Easy | `1` | $1.00 | 0.40 | Find the current stock price of Reliance |
| Medium | `2` | $0.60 | 1.00 | Analyze HDFC Bank's Q3 revenue growth |
| Hard | `3` | $0.25 | 1.00 | Verify the official dividend payout for Palantir |

**Task 1 (Easy):** Generous budget, low confidence target. A single `SEARCH` call clears it. Designed to orient the agent and confirm basic environment mechanics work.

**Task 2 (Medium):** Tighter budget with a full-confidence target. Requires careful tool selection — a naive strategy that jumps straight to `VERIFY` without sufficient confidence will waste budget and fail the lock gate.

**Task 3 (Hard):** Budget of $0.25 allows only a handful of tools (e.g., 25× `SCRAPE`, or 2× `SEARCH` + 1× `SCRAPE`). Reaching full confidence within budget requires near-optimal sequencing.

---

## Baseline Performance

The following results were produced by running `inference.py` with the default `gpt-4o-mini` model against a local server instance:

| Task | Difficulty | Starting Budget | Target Confidence | Baseline Score |
|---|---|---|---|---|
| Task 1 | Easy | $1.00 | 0.40 | **0.95** |
| Task 2 | Medium | $0.60 | 1.00 | **0.78** |
| Task 3 | Hard | $0.25 | 1.00 | **0.42** |

Scores represent `grader_score` (partial credit for confidence progress) rather than binary pass/fail. Task 3's lower score reflects the genuine difficulty of hitting full confidence on a $0.25 budget.

---

## Project Architecture

```
.
├── inference.py                  # LLM agent that runs all 3 tasks end-to-end
├── openenv.yaml                  # OpenEnv manifest (name, runtime, app entrypoint)
├── README.md                     # This file
├── requirements.txt              # Pip-installable dependencies
├── pyproject.toml                # Package metadata and uv/setuptools config
├── __init__.py                   # Package exports (Action, Observation, Client)
├── client.py                     # OpenEnv EnvClient subclass for HTTP interaction
├── models.py                     # Pydantic models: Action and Observation types
└── server/
    ├── __init__.py               # Exports FrugalApiEconomyEnvironment
    ├── app.py                    # FastAPI app wired to OpenEnv HTTP server
    ├── Dockerfile                # Container image for Hugging Face Spaces
    ├── requirements.txt          # Server-side dependencies
    └── frugal_api_economy_environment.py  # Core environment logic
        static/
        ├── dashboard.html        # Interactive web console
        ├── dashboard.css         # Dashboard styles
        └── dashboard.js          # Dashboard frontend logic
```

### Component Roles

**`models.py`** — Defines the typed contract between agent and environment using Pydantic + OpenEnv base types:
- `FrugalApiEconomyAction` — validates `tool_name` (enum) and `query` (string, 3–512 chars)
- `FrugalApiEconomyObservation` — carries budget, confidence, info, termination reason, reward, and metadata

**`server/frugal_api_economy_environment.py`** — The environment itself. Implements the OpenEnv `Environment` interface with:
- `reset(task_id)` — initializes budget, confidence, and task config
- `step(action)` — applies tool cost, updates confidence, computes reward, checks termination
- `state` property — returns current episode ID and step count
- `get_grader_score()` — computes continuous progress score

**`server/app.py`** — Wraps the environment in a FastAPI application via `openenv.core.env_server.http_server.create_app`. Adds routes for the web dashboard (`/web`) and static file serving (`/assets`).

**`client.py`** — A typed Python client (`FrugalApiEconomyEnv`) that extends `EnvClient` from `openenv-core`. Handles serialization of actions into HTTP payloads and deserialization of server responses back into typed `FrugalApiEconomyObservation` objects.

**`inference.py`** — The reference agent. Uses the OpenAI client to query an LLM (default: `gpt-4o-mini` via HuggingFace Router) for tool decisions. Loops over all 3 tasks, logs structured `[START]`, `[STEP]`, and `[END]` lines to stdout, and records grader scores.

**`server/static/`** — A fully self-contained browser-based dashboard for playing the environment manually. Shows live budget, confidence bar, tool cards (with VERIFY lock state), step history, and episode return.

---

## Setup & Installation

### Prerequisites

- Python 3.10 or higher
- `pip` or [`uv`](https://github.com/astral-sh/uv) (recommended)

### Install with pip

```bash
# Clone the repo
git clone https://github.com/your-username/frugal-api-economy
cd frugal-api-economy

# Install dependencies
pip install -r requirements.txt
```

### Install with uv (faster)

```bash
uv sync
```

---

## Running the Server

Start the FastAPI environment server locally:

```bash
# With uvicorn directly
uvicorn server.app:app --host 0.0.0.0 --port 8000

# Or via the package entrypoint (if installed)
python -m server.app --host 0.0.0.0 --port 8000
```

The server will be available at:
- **API:** `http://localhost:8000`
- **Web Dashboard:** `http://localhost:8000/web`
- **Health check:** `http://localhost:8000/health`
- **OpenAPI docs:** `http://localhost:8000/docs`

---

## Running the Inference Agent

With the server running, run the LLM agent against all 3 tasks:

```bash
# Minimum — uses HF Router with gpt-4o-mini
HF_TOKEN=hf_your_token_here python inference.py

# Custom model or base URL
API_BASE_URL=https://api.openai.com/v1 \
MODEL_NAME=gpt-4o \
HF_TOKEN=sk-your-key-here \
python inference.py
```

The agent prints structured logs to stdout:

```
[START] task=frugal_task_1 env=frugal_api_economy model=gpt-4o-mini
[STEP] step=1 action=SEARCH reward=-5.00 done=false error=null
[STEP] step=2 action=LLM_REASON reward=-2.50 done=false error=null
[STEP] step=3 action=VERIFY reward=87.50 done=true error=null
[END] success=true steps=3 score=1.000 rewards=-5.00,-2.50,87.50
```

---

## Running with Docker

```bash
# Build the image
docker build -f server/Dockerfile -t frugal-api-economy .

# Run the container
docker run -p 8000:8000 frugal-api-economy
```

The Dockerfile uses a multi-stage build:
1. **Builder stage** — installs `uv`, syncs dependencies from `pyproject.toml` (or `uv.lock` if present) into a virtual environment
2. **Runtime stage** — copies only the `.venv` and source, sets `PYTHONPATH`, and launches `uvicorn`

---

## Environment Variables

### For `inference.py` (agent)

| Variable | Default | Required | Description |
|---|---|---|---|
| `HF_TOKEN` | — | **Yes** | API key for the LLM provider (HuggingFace token or OpenAI key) |
| `API_BASE_URL` | `https://router.huggingface.co/v1` | No | OpenAI-compatible base URL for LLM calls |
| `MODEL_NAME` | `gpt-4o-mini` | No | Model identifier passed to the OpenAI client |
| `ENV_BASE_URL` | `http://localhost:8000` | No | Base URL of the running environment server |

> `HF_TOKEN` intentionally has **no default**. The agent will pass `None` as the API key if this is unset, which will likely cause authentication errors at inference time.

### For the server

The server itself requires no environment variables for basic operation. It binds to `0.0.0.0:8000` by default.

---

## Web Dashboard

The interactive dashboard at `/web` lets you play the environment manually in a browser:

- **Task selector** — switch between Easy, Medium, and Hard tasks
- **Reset Episode** — initializes a fresh episode for the selected task
- **Wallet panel** — shows remaining budget with a low-runway warning pulse
- **Confidence bar** — animated progress bar with a marker at the task's target confidence
- **Tool marketplace** — click to execute a tool; VERIFY card is disabled until confidence ≥ 0.50
- **Audit trail** — timestamped log of every step with reward and running episode return

The dashboard communicates directly with the FastAPI server via `/reset` and `/step` endpoints.

---

## Python Client Usage

```python
from frugal_api_economy import FrugalApiEconomyAction, FrugalApiEconomyEnv

# Basic episode loop
with FrugalApiEconomyEnv(base_url="http://localhost:8000") as env:

    # Start Task 1 (Easy)
    result = env.reset(task_id=1)
    print(result.observation.info)
    # "Task 1 (Easy): Find the current stock price of Reliance. 
    #  Starting budget: $1.00. Target confidence: 0.40."

    # Take a step
    result = env.step(FrugalApiEconomyAction(
        tool_name="SEARCH",
        query="Reliance Industries current stock price NSE",
    ))
    obs = result.observation
    print(f"Budget: ${obs.budget_remaining:.2f}  Confidence: {obs.confidence:.2f}  Reward: {result.reward:.2f}")
    # Budget: $0.90  Confidence: 0.40  Reward: 90.00

    print(obs.done, obs.termination_reason)
    # True  confidence_reached
```

```python
# Scripted strategy across all tasks
strategy_by_task = {
    1: ["SEARCH"],                          # One SEARCH clears Task 1
    2: ["SCRAPE", "SEARCH", "SEARCH"],     # Build to 0.60, then two SEARCHes for 1.00
    3: ["SCRAPE", "SCRAPE", "SCRAPE",      # Stay cheap, hope for VERIFY gate
        "LLM_REASON", "VERIFY"],
}

with FrugalApiEconomyEnv(base_url="http://localhost:8000") as env:
    for task_id, tools in strategy_by_task.items():
        result = env.reset(task_id=task_id)
        for tool in tools:
            if result.done:
                break
            result = env.step(FrugalApiEconomyAction(
                tool_name=tool,
                query=f"research step for task {task_id}",
            ))
        score = result.observation.metadata.get("grader_score", 0.0)
        print(f"Task {task_id}: grader_score={score:.2f}  done={result.done}")
```

---

## API Endpoints

The server exposes the standard OpenEnv HTTP interface:

| Method | Path | Description |
|---|---|---|
| `POST` | `/reset` | Start a new episode. Body: `{"task_id": 1}` |
| `POST` | `/step` | Execute one action. Body: `{"action": {"tool_name": "SEARCH", "query": "..."}}` |
| `GET` | `/state` | Return current episode state (episode ID, step count) |
| `GET` | `/health` | Health check — returns `200 OK` when server is ready |
| `GET` | `/web` | Serves the interactive web dashboard |
| `GET` | `/docs` | Auto-generated OpenAPI documentation |

### Example: `/reset`

```bash
curl -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": 2}'
```

```json
{
  "observation": {
    "budget_remaining": 0.6,
    "confidence": 0.0,
    "info": "Task 2 (Medium): Analyze HDFC Bank's Q3 revenue growth. Starting budget: $0.60. Target confidence: 1.00.",
    "termination_reason": "",
    "done": false,
    "reward": 0.0,
    "metadata": {"task_id": 2, "target_confidence": 1.0, "grader_score": 0.0}
  },
  "done": false
}
```

### Example: `/step`

```bash
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"action": {"tool_name": "SCRAPE", "query": "HDFC Q3 revenue overview"}}'
```

```json
{
  "observation": {
    "budget_remaining": 0.59,
    "confidence": 0.2,
    "info": "Used SCRAPE for 'HDFC Q3 revenue overview'. Confidence increased to 0.20. Budget remaining: $0.59. Reward this step: -0.50. Episode return: -0.50.",
    "termination_reason": "",
    "done": false,
    "reward": -0.5,
    "metadata": {
      "task_id": 2, "target_confidence": 1.0, "tool": "SCRAPE",
      "cost": 0.01, "step_count": 1, "grader_score": 0.2,
      "episode_return": -0.5, "total_spent": 0.01
    }
  },
  "reward": -0.5,
  "done": false
}
```

---

## Development

### Running Tests

```bash
pip install -e ".[dev]"
pytest
```

### Validating with OpenEnv CLI

```bash
openenv validate
```

This checks that `openenv.yaml` is well-formed, the server starts correctly, `/reset` returns HTTP 200, and the environment conforms to the OpenEnv spec.

### Project Conventions

- Environment logic lives entirely in `server/frugal_api_economy_environment.py` — the FastAPI layer in `server/app.py` is intentionally thin
- All monetary values are stored as Python `float` with `round(..., 4)` to avoid floating-point drift across steps
- The grader score is computed live in `get_grader_score()` and embedded in every `step()` response's metadata — no separate scoring pass needed
- `SUPPORTS_CONCURRENT_SESSIONS = True` is set on the environment class, meaning the OpenEnv server can run multiple isolated episodes simultaneously

---

## License

MIT © 2026 Abhinav